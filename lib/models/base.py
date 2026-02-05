#!/usr/bin/env python3
"""
Base model class for Creative Workflow
Abstract base class that all model implementations inherit from
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class BaseModel(ABC):
    """Abstract base class for all diffusion models"""

    def __init__(self, model_config: Dict, model_path: str):
        """
        Initialize base model

        Args:
            model_config: Model configuration from presets.json
            model_path: Full path to model file or HuggingFace ID
        """
        self.config = model_config
        self.model_path = model_path
        self.pipeline = None
        self.device = None
        self.current_lora = None

        # Extract settings
        self.settings = model_config.get("settings", {})
        self.default_steps = self.settings.get("steps", 20)
        self.default_guidance = self.settings.get("guidance_scale", 7.5)
        self.default_resolution = self.settings.get("resolution", 1024)
        self.supports_negative_prompt = self.settings.get("supports_negative_prompt", False)
        self.max_sequence_length = self.settings.get("max_sequence_length")

        # Behavior flags (for refactored template methods)
        self.force_default_guidance = self.settings.get("force_default_guidance", False)
        self.use_sequential_cpu_offload = self.settings.get("use_sequential_cpu_offload", False)
        self.enable_vae_slicing = self.settings.get("enable_vae_slicing", False)
        self.enable_debug_logging = self.settings.get("enable_debug_logging", False)

        # Scheduler configuration
        self.default_scheduler = self.settings.get("scheduler")
        self._original_scheduler_config = None  # Store original for restoration

        # Get dtype — FP8 variants can't be used as torch_dtype for loading,
        # so fall back to bfloat16 (weights are upcast automatically).
        dtype_str = self.settings.get("dtype", "bfloat16")
        if dtype_str.startswith("float8"):
            self.dtype = torch.bfloat16
        else:
            self.dtype = getattr(torch, dtype_str, torch.bfloat16)

    def load_pipeline(self, progress_callback=None) -> str:
        """
        Template method for pipeline loading (common flow)

        Subclasses should NOT override this method. Instead, override
        _create_pipeline() to specify how to load the pipeline.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Status message
        """
        if self.pipeline is not None:
            logger.debug(f"Pipeline already loaded for {self.model_name}, skipping load_pipeline")
            return "Model already loaded"

        logger.info(f"Loading pipeline for {self.model_name}")
        logger.debug(f"Model path: {self.model_path}")
        logger.debug(
            f"Model settings: steps={self.default_steps}, guidance={self.default_guidance}, dtype={self.dtype}"
        )

        try:
            # Step 1: Device setup
            if progress_callback:
                progress_callback(0, desc="Setting up device...")
            logger.debug("Step 1: Setting up device")
            device, device_name = self.setup_device()

            # Step 2: Load pipeline (model-specific)
            if progress_callback:
                progress_callback(0.3, desc=f"Loading {self.model_name} pipeline...")
            logger.debug(f"Step 2: Creating pipeline via _create_pipeline()")

            self.pipeline = self._create_pipeline()
            logger.debug(f"Pipeline created: {type(self.pipeline).__name__}")

            # Step 2.5: Store original scheduler config for potential restoration
            if hasattr(self.pipeline, "scheduler") and hasattr(self.pipeline.scheduler, "config"):
                self._original_scheduler_config = self.pipeline.scheduler.config
                logger.debug(
                    f"Stored original scheduler config: {self.pipeline.scheduler.__class__.__name__}"
                )

            # Step 2.6: Apply default scheduler if configured
            if self.default_scheduler:
                if progress_callback:
                    progress_callback(0.5, desc=f"Setting scheduler: {self.default_scheduler}...")
                logger.debug(f"Step 2.5: Setting default scheduler: {self.default_scheduler}")
                self.set_scheduler(self.default_scheduler)

            # Step 3: Apply optimizations
            if progress_callback:
                progress_callback(0.7, desc="Enabling optimizations...")
            logger.debug("Step 3: Applying device optimizations")

            self._apply_device_optimizations()

            if progress_callback:
                progress_callback(1.0, desc="Model loaded successfully!")

            logger.info(f"Pipeline loaded successfully: {self.model_name} on {device_name}")
            return f"{self.model_name} loaded on {device_name}"

        except Exception as e:
            logger.error(f"Error loading pipeline for {self.model_name}: {e}", exc_info=True)
            return f"Error loading {self.model_name}: {e}"

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        clip_skip: Optional[int] = None,
        scheduler: Optional[str] = None,
        progress_callback=None,
    ) -> Tuple[Image.Image, Dict]:
        """
        Template method for image generation (common flow)

        Subclasses should NOT override this method. Instead, override
        the hooks (_build_prompts, _build_pipeline_kwargs, etc.) to
        customize behavior.

        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt (if supported)
            steps: Number of inference steps
            guidance_scale: Guidance scale
            width: Image width
            height: Image height
            seed: Random seed
            clip_skip: Number of CLIP layers to skip (if supported)
            scheduler: Scheduler class name to use (overrides default)
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (generated image, metadata dict)
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        logger.debug(f"generate() called for {self.model_name}")
        logger.debug(
            f"Input prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Input prompt: {prompt}"
        )
        logger.debug(
            f"Generation params: steps={steps}, guidance={guidance_scale}, size={width}x{height}, seed={seed}"
        )

        # Step 0: Apply scheduler override if provided
        scheduler_applied = None
        if scheduler:
            logger.debug(f"Step 0: Applying scheduler override: {scheduler}")
            scheduler_applied = self.set_scheduler(scheduler)

        # Step 1: Apply parameter defaults and overrides
        logger.debug("Step 1: Preparing generation parameters")
        params = self._prepare_generation_params(
            prompt, negative_prompt, steps, guidance_scale, width, height, seed, clip_skip
        )
        # Track which scheduler is active for metadata
        params["scheduler"] = scheduler_applied or self._get_current_scheduler_name()
        logger.debug(
            f"Resolved params: steps={params['steps']}, guidance={params['guidance_scale']}, scheduler={params['scheduler']}"
        )

        # Step 2: Build prompts with LoRA suffixes (hook for customization)
        logger.debug("Step 2: Building prompts with LoRA suffixes")
        params = self._build_prompts(params)
        logger.debug(f"Final prompt length: {len(params['prompt'])} chars")

        # Step 3: Build pipeline kwargs (hook for model-specific parameters)
        logger.debug("Step 3: Building pipeline kwargs")
        gen_kwargs = self._build_pipeline_kwargs(params, progress_callback)
        logger.debug(f"Pipeline kwargs keys: {list(gen_kwargs.keys())}")

        # Step 3.5: Pre-generation VAE check (for debugging black images on MPS)
        if self.device.type == "mps" and hasattr(self.pipeline, "vae"):
            logger.debug(
                f"[MPS VAE check] device: {self.pipeline.vae.device}, dtype: {self.pipeline.vae.dtype}"
            )
            if self.pipeline.vae.dtype != torch.float32:
                logger.warning(f"[MPS VAE check] VAE is NOT float32! Fixing now...")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
                logger.debug(
                    f"[MPS VAE check] VAE after fix: {self.pipeline.vae.device}, dtype: {self.pipeline.vae.dtype}"
                )

        # Step 4: Generate image
        logger.debug("Step 4: Calling pipeline for generation")
        image = self.pipeline(**gen_kwargs).images[0]
        logger.debug(f"Generation complete, image size: {image.size}")

        # Step 5: Cleanup
        logger.debug("Step 5: Clearing cache")
        self.clear_cache()

        # Step 6: Build metadata
        logger.debug("Step 6: Building metadata")
        metadata = self._build_metadata(params)

        logger.info(
            f"Image generated successfully: {params['width']}x{params['height']}, {params['steps']} steps"
        )
        return image, metadata

    @abstractmethod
    def _create_pipeline(self):
        """
        Create and return the pipeline instance (model-specific)

        This method must be overridden by subclasses to load their specific
        pipeline type (e.g., FluxPipeline, StableDiffusionXLPipeline, etc.)

        Returns:
            Pipeline instance
        """
        pass

    def _prepare_generation_params(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        steps: Optional[int],
        guidance_scale: Optional[float],
        width: Optional[int],
        height: Optional[int],
        seed: Optional[int],
        clip_skip: Optional[int],
    ) -> Dict:
        """
        Prepare generation parameters with defaults and overrides

        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt
            steps: Number of inference steps
            guidance_scale: Guidance scale
            width: Image width
            height: Image height
            seed: Random seed
            clip_skip: CLIP skip layers

        Returns:
            Dictionary of prepared parameters
        """
        # Apply config defaults
        steps = steps or self.default_steps
        width = width or self.default_resolution
        height = height or self.default_resolution

        # Handle guidance_scale with model-specific override behavior
        guidance_scale = self._resolve_guidance_scale(guidance_scale)

        # Apply LoRA clip_skip override
        effective_clip_skip = self.get_lora_clip_skip() or clip_skip

        return {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "clip_skip": effective_clip_skip,
        }

    def _resolve_guidance_scale(self, guidance_scale: Optional[float]) -> float:
        """
        Resolve final guidance scale with LoRA and model-specific overrides

        Args:
            guidance_scale: Guidance scale parameter (may be None)

        Returns:
            Resolved guidance scale value
        """
        # Check if model forces guidance override (turbo models)
        if self.force_default_guidance:
            # Turbo models MUST use their default guidance - don't allow overrides
            return self.default_guidance

        # Use parameter or default
        guidance_scale = guidance_scale if guidance_scale is not None else self.default_guidance

        # LoRA takes precedence (but only if model doesn't force default)
        lora_guidance = self.get_lora_guidance_scale()
        if lora_guidance is not None:
            guidance_scale = lora_guidance

        return guidance_scale

    def _build_prompts(self, params: Dict) -> Dict:
        """
        Build final prompts with LoRA suffixes

        Override this method for token limiting or special prompt handling.

        Args:
            params: Parameter dictionary from _prepare_generation_params()

        Returns:
            Updated parameter dictionary with modified prompts
        """
        # Append LoRA prompt suffix
        lora_suffix = self.get_lora_prompt_suffix()
        if lora_suffix:
            params["prompt"] = f"{params['prompt']}, {lora_suffix}"

        # Append LoRA negative prompt suffix (if model supports it)
        if self.supports_negative_prompt and params["negative_prompt"]:
            lora_neg_suffix = self.get_lora_negative_prompt_suffix()
            if lora_neg_suffix:
                params["negative_prompt"] = f"{params['negative_prompt']}, {lora_neg_suffix}"

        # Model-specific prompt handling (e.g., Qwen requires space for empty negative)
        params = self._handle_special_prompt_requirements(params)

        return params

    def _handle_special_prompt_requirements(self, params: Dict) -> Dict:
        """
        Handle model-specific prompt requirements

        Override this method if your model has special requirements
        (e.g., Qwen requires space for empty negative prompt)

        Args:
            params: Parameter dictionary

        Returns:
            Updated parameter dictionary
        """
        return params

    def _build_pipeline_kwargs(self, params: Dict, progress_callback) -> Dict:
        """
        Build kwargs for pipeline call

        Override this method for model-specific parameters
        (e.g., max_sequence_length, true_cfg_scale, callbacks)

        Args:
            params: Parameter dictionary from _build_prompts()
            progress_callback: Optional progress callback

        Returns:
            Dictionary of kwargs for pipeline call
        """
        # Setup generator
        generator = torch.Generator(device="cpu")
        if params["seed"] is not None:
            generator.manual_seed(params["seed"])

        # Base kwargs
        gen_kwargs = {
            "num_inference_steps": params["steps"],
            "guidance_scale": params["guidance_scale"],
            "height": params["height"],
            "width": params["width"],
            "generator": generator,
        }

        # Base kwargs
        gen_kwargs["prompt"] = params["prompt"]

        # Add negative prompt if supported
        if self.supports_negative_prompt and params.get("negative_prompt"):
            gen_kwargs["negative_prompt"] = params["negative_prompt"]

        # Add clip_skip if set
        if params["clip_skip"] is not None:
            gen_kwargs["clip_skip"] = params["clip_skip"]

        # Add max_sequence_length if configured
        if self.max_sequence_length is not None:
            gen_kwargs["max_sequence_length"] = self.max_sequence_length

        return gen_kwargs

    def _build_metadata(self, params: Dict) -> Dict:
        """
        Build metadata dictionary for generated image

        Args:
            params: Parameter dictionary

        Returns:
            Metadata dictionary
        """
        metadata = {
            "model": self.model_name,
            "prompt": params["prompt"],
            "steps": params["steps"],
            "guidance_scale": params["guidance_scale"],
            "width": params["width"],
            "height": params["height"],
            "seed": params["seed"],
            "scheduler": params.get("scheduler"),
            "lora": self.current_lora["label"] if self.current_lora else None,
        }

        # Add negative prompt if supported
        if self.supports_negative_prompt:
            metadata["negative_prompt"] = params.get("negative_prompt")

        # Add max_sequence_length if used
        if self.max_sequence_length is not None:
            metadata["max_sequence_length"] = self.max_sequence_length

        return metadata

    def _apply_device_optimizations(self) -> None:
        """
        Apply device-specific optimizations to pipeline

        Override this method if your model needs custom optimizations
        """
        device = self.device
        logger.debug(f"Applying device optimizations for: {device.type}")

        if device.type == "mps":
            # For MPS, keep VAE on device but force float32 to avoid NaN values
            # Moving VAE to CPU causes device mismatch errors without offload
            if hasattr(self.pipeline, "vae"):
                logger.debug("[MPS] Converting VAE to float32 (keeping on MPS)")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
                # Enable VAE slicing for better memory usage and numerical stability
                if hasattr(self.pipeline.vae, "enable_slicing"):
                    logger.debug("[MPS] Enabling VAE slicing")
                    self.pipeline.vae.enable_slicing()
                if hasattr(self.pipeline.vae, "enable_tiling"):
                    logger.debug("[MPS] Enabling VAE tiling")
                    self.pipeline.vae.enable_tiling()

            # Move entire pipeline to MPS
            logger.debug("[MPS] Moving pipeline to MPS device")
            self.pipeline.to(device)
            logger.debug("[MPS] Enabling attention slicing")
            self.pipeline.enable_attention_slicing()

            # Ensure VAE is still float32 after pipeline.to()
            if hasattr(self.pipeline, "vae"):
                logger.debug("[MPS] Re-confirming VAE float32 after pipeline.to()")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
        elif device.type == "cuda":
            # Default to model_cpu_offload (override if needed)
            if self.use_sequential_cpu_offload:
                logger.debug("[CUDA] Enabling sequential CPU offload")
                self.pipeline.enable_sequential_cpu_offload(device=device)
            else:
                logger.debug("[CUDA] Enabling model CPU offload")
                self.pipeline.enable_model_cpu_offload()
            logger.debug("[CUDA] Enabling attention slicing")
            self.pipeline.enable_attention_slicing()
        else:
            logger.debug(f"[CPU] Moving pipeline to {device}")
            self.pipeline = self.pipeline.to(device)

        logger.debug("Device optimizations applied successfully")

    def set_scheduler(self, scheduler_name: str) -> Optional[str]:
        """
        Set the scheduler for the pipeline by class name.

        Args:
            scheduler_name: Name of the scheduler class (e.g., 'EulerDiscreteScheduler',
                           'DPMSolverMultistepScheduler', 'FlowMatchEulerDiscreteScheduler')

        Returns:
            Name of the scheduler that was set, or None if failed
        """
        if self.pipeline is None:
            logger.debug("Cannot set scheduler: pipeline not loaded")
            return None

        if not hasattr(self.pipeline, "scheduler"):
            logger.debug("Cannot set scheduler: pipeline has no scheduler attribute")
            return None

        logger.debug(f"Setting scheduler: {scheduler_name}")

        try:
            # Import diffusers schedulers dynamically
            import diffusers

            # Get the scheduler class by name
            if not hasattr(diffusers, scheduler_name):
                logger.warning(
                    f"Scheduler '{scheduler_name}' not found in diffusers, keeping current scheduler"
                )
                return None

            scheduler_class = getattr(diffusers, scheduler_name)

            # Create new scheduler from current scheduler's config
            # This preserves model-specific scheduler parameters
            logger.debug(f"Creating {scheduler_name} from existing config")
            new_scheduler = scheduler_class.from_config(self.pipeline.scheduler.config)
            self.pipeline.scheduler = new_scheduler

            logger.info(f"Scheduler set to: {scheduler_name}")
            return scheduler_name

        except Exception as e:
            logger.warning(f"Failed to set scheduler '{scheduler_name}': {e}")
            return None

    def _get_current_scheduler_name(self) -> Optional[str]:
        """Get the current scheduler's class name."""
        if self.pipeline is None or not hasattr(self.pipeline, "scheduler"):
            return None
        return self.pipeline.scheduler.__class__.__name__

    def _post_lora_load_fixes(self) -> None:
        """
        Re-apply device-specific fixes after LoRA loading

        LoRA loading can move pipeline components or change their dtypes.
        Override this method to re-apply critical fixes (e.g., VAE float32 on MPS).

        Default implementation does nothing.
        """
        pass

    def _post_lora_unload_fixes(self) -> None:
        """
        Re-apply device-specific fixes after LoRA unloading

        LoRA unloading can move pipeline components or change their dtypes.
        Override this method to re-apply critical fixes (e.g., VAE float32 on MPS).

        Default implementation does nothing.
        """
        pass

    def setup_device(self) -> Tuple[torch.device, str]:
        """
        Configure device for Apple Silicon optimization

        Returns:
            Tuple of (device, device_name)
        """
        logger.debug("Detecting available compute device")
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            device_name = "MPS (Apple Silicon)"
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            device_name = "CUDA"
        else:
            device = torch.device("cpu")
            device_name = "CPU"

        self.device = device
        logger.info(f"Device configured: {device_name}")
        return device, device_name

    def load_lora(self, lora_path: str, lora_config: Dict) -> str:
        """
        Load a LoRA adapter

        Args:
            lora_path: Path to LoRA file
            lora_config: LoRA configuration from presets

        Returns:
            Status message
        """
        if self.pipeline is None:
            logger.warning("Attempted to load LoRA but pipeline not loaded")
            return "Error: Model not loaded yet"

        logger.info(f"Loading LoRA: {lora_config.get('label', 'unknown')}")
        logger.debug(f"LoRA path: {lora_path}")

        try:
            # Unload previous LoRA if any
            if self.current_lora is not None:
                logger.debug(f"Unloading previous LoRA: {self.current_lora.get('label')}")
                try:
                    self.pipeline.unload_lora_weights()
                except Exception:
                    pass

            # Load new LoRA
            if not Path(lora_path).exists():
                logger.error(f"LoRA file not found: {lora_path}")
                return f"Error: LoRA file not found: {lora_path}"

            # Get LoRA strength from settings
            strength = lora_config.get("settings", {}).get("strength", 1.0)
            logger.debug(f"LoRA strength: {strength}")

            # Load LoRA weights
            logger.debug("Loading LoRA weights into pipeline")
            self.pipeline.load_lora_weights(lora_path, adapter_name="default")

            # Set LoRA scale if applicable
            if hasattr(self.pipeline, "set_adapters"):
                logger.debug(f"Setting adapter weights: {strength}")
                self.pipeline.set_adapters(["default"], adapter_weights=[strength])

            # CRITICAL: Re-apply device-specific fixes after LoRA loading
            # LoRA loading can move components or change dtypes
            logger.debug("Applying post-LoRA load fixes")
            self._post_lora_load_fixes()

            self.current_lora = lora_config

            logger.info(f"LoRA loaded successfully: {lora_config['label']} (strength: {strength})")
            return f"LoRA loaded: {lora_config['label']} (strength: {strength})"

        except Exception as e:
            logger.error(f"Error loading LoRA: {e}", exc_info=True)
            return f"Error loading LoRA: {e}"

    def unload_lora(self) -> str:
        """
        Unload current LoRA

        Returns:
            Status message
        """
        if self.pipeline is None:
            logger.warning("Attempted to unload LoRA but pipeline not loaded")
            return "Error: Model not loaded yet"

        if self.current_lora is None:
            logger.debug("No LoRA to unload")
            return "No LoRA loaded"

        lora_label = self.current_lora.get("label", "unknown")
        logger.info(f"Unloading LoRA: {lora_label}")

        try:
            logger.debug("Calling pipeline.unload_lora_weights()")
            self.pipeline.unload_lora_weights()

            # CRITICAL: Re-apply device-specific fixes after LoRA unloading
            # LoRA unloading can move components or change dtypes
            logger.debug("Applying post-LoRA unload fixes")
            self._post_lora_unload_fixes()

            self.current_lora = None
            logger.info(f"LoRA unloaded successfully: {lora_label}")
            return "LoRA unloaded"
        except Exception as e:
            logger.warning(f"Exception during LoRA unload (resetting anyway): {e}")
            self.current_lora = None
            return "LoRA reset"

    def get_lora_prompt_suffix(self) -> str:
        """Get prompt suffix from current LoRA"""
        if self.current_lora is None:
            return ""
        return self.current_lora.get("prompt", "")

    def get_lora_negative_prompt_suffix(self) -> str:
        """Get negative prompt suffix from current LoRA"""
        if self.current_lora is None:
            return ""
        return self.current_lora.get("negative_prompt", "")

    def get_lora_clip_skip(self) -> Optional[int]:
        """Get clip_skip value from current LoRA"""
        if self.current_lora is None:
            return None
        return self.current_lora.get("settings", {}).get("clip_skip")

    def get_lora_guidance_scale(self) -> Optional[float]:
        """Get guidance_scale value from current LoRA"""
        if self.current_lora is None:
            return None
        return self.current_lora.get("settings", {}).get("guidance_scale")

    def clear_cache(self) -> None:
        """Clear GPU memory cache"""
        if self.device is None:
            return

        logger.debug(f"Clearing {self.device.type} cache")
        if self.device.type == "mps":
            torch.mps.empty_cache()
        elif self.device.type == "cuda":
            torch.cuda.empty_cache()

    def is_loaded(self) -> bool:
        """Check if pipeline is loaded"""
        return self.pipeline is not None

    @property
    def model_name(self) -> str:
        """Get model label"""
        return self.config.get("label", "Unknown Model")

    @property
    def model_slug(self) -> str:
        """Get model slug"""
        return self.config.get("slug", "unknown")
