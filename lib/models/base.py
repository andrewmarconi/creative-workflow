#!/usr/bin/env python3
"""
Base model class for Creative Workflow
Abstract base class that all model implementations inherit from
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
from PIL import Image


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
            return "Model already loaded"

        try:
            # Step 1: Device setup
            if progress_callback:
                progress_callback(0, desc="Setting up device...")
            device, device_name = self.setup_device()

            # Step 2: Load pipeline (model-specific)
            if progress_callback:
                progress_callback(0.3, desc=f"Loading {self.model_name} pipeline...")

            self.pipeline = self._create_pipeline()

            # Step 3: Apply optimizations
            if progress_callback:
                progress_callback(0.7, desc="Enabling optimizations...")

            self._apply_device_optimizations()

            if progress_callback:
                progress_callback(1.0, desc="Model loaded successfully!")

            return f"{self.model_name} loaded on {device_name}"

        except Exception as e:
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
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (generated image, metadata dict)
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        # Step 1: Apply parameter defaults and overrides
        params = self._prepare_generation_params(
            prompt, negative_prompt, steps, guidance_scale,
            width, height, seed, clip_skip
        )

        # Step 2: Build prompts with LoRA suffixes (hook for customization)
        params = self._build_prompts(params)

        # Step 3: Build pipeline kwargs (hook for model-specific parameters)
        gen_kwargs = self._build_pipeline_kwargs(params, progress_callback)

        # Step 4: Generate image
        image = self.pipeline(**gen_kwargs).images[0]

        # Step 5: Cleanup
        self.clear_cache()

        # Step 6: Build metadata
        metadata = self._build_metadata(params)

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
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'steps': steps,
            'guidance_scale': guidance_scale,
            'width': width,
            'height': height,
            'seed': seed,
            'clip_skip': effective_clip_skip,
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
            params['prompt'] = f"{params['prompt']}, {lora_suffix}"

        # Append LoRA negative prompt suffix (if model supports it)
        if self.supports_negative_prompt and params['negative_prompt']:
            lora_neg_suffix = self.get_lora_negative_prompt_suffix()
            if lora_neg_suffix:
                params['negative_prompt'] = f"{params['negative_prompt']}, {lora_neg_suffix}"

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
        if params['seed'] is not None:
            generator.manual_seed(params['seed'])

        # Base kwargs
        gen_kwargs = {
            'prompt': params['prompt'],
            'num_inference_steps': params['steps'],
            'guidance_scale': params['guidance_scale'],
            'height': params['height'],
            'width': params['width'],
            'generator': generator,
        }

        # Add negative prompt if supported
        if self.supports_negative_prompt and params['negative_prompt']:
            gen_kwargs['negative_prompt'] = params['negative_prompt']

        # Add clip_skip if set
        if params['clip_skip'] is not None:
            gen_kwargs['clip_skip'] = params['clip_skip']

        # Add max_sequence_length if configured
        if self.max_sequence_length is not None:
            gen_kwargs['max_sequence_length'] = self.max_sequence_length

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
            'model': self.model_name,
            'prompt': params['prompt'],
            'steps': params['steps'],
            'guidance_scale': params['guidance_scale'],
            'width': params['width'],
            'height': params['height'],
            'seed': params['seed'],
            'lora': self.current_lora['label'] if self.current_lora else None,
        }

        # Add negative prompt if supported
        if self.supports_negative_prompt:
            metadata['negative_prompt'] = params.get('negative_prompt')

        # Add max_sequence_length if used
        if self.max_sequence_length is not None:
            metadata['max_sequence_length'] = self.max_sequence_length

        return metadata

    def _apply_device_optimizations(self) -> None:
        """
        Apply device-specific optimizations to pipeline

        Override this method if your model needs custom optimizations
        """
        device = self.device

        if device.type == "mps":
            self.pipeline.enable_sequential_cpu_offload(device=device)
            self.pipeline.enable_attention_slicing()
        elif device.type == "cuda":
            # Default to model_cpu_offload (override if needed)
            if self.use_sequential_cpu_offload:
                self.pipeline.enable_sequential_cpu_offload(device=device)
            else:
                self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_attention_slicing()
        else:
            self.pipeline = self.pipeline.to(device)

    def setup_device(self) -> Tuple[torch.device, str]:
        """
        Configure device for Apple Silicon optimization

        Returns:
            Tuple of (device, device_name)
        """
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
            return "Error: Model not loaded yet"

        try:
            # Unload previous LoRA if any
            if self.current_lora is not None:
                try:
                    self.pipeline.unload_lora_weights()
                except Exception:
                    pass

            # Load new LoRA
            if not Path(lora_path).exists():
                return f"Error: LoRA file not found: {lora_path}"

            # Get LoRA strength from settings
            strength = lora_config.get("settings", {}).get("strength", 1.0)

            # Load LoRA weights
            self.pipeline.load_lora_weights(lora_path, adapter_name="default")

            # Set LoRA scale if applicable
            if hasattr(self.pipeline, "set_adapters"):
                self.pipeline.set_adapters(["default"], adapter_weights=[strength])

            self.current_lora = lora_config

            return f"LoRA loaded: {lora_config['label']} (strength: {strength})"

        except Exception as e:
            return f"Error loading LoRA: {e}"

    def unload_lora(self) -> str:
        """
        Unload current LoRA

        Returns:
            Status message
        """
        if self.pipeline is None:
            return "Error: Model not loaded yet"

        if self.current_lora is None:
            return "No LoRA loaded"

        try:
            self.pipeline.unload_lora_weights()
            self.current_lora = None
            return "LoRA unloaded"
        except Exception:
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
