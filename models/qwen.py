#!/usr/bin/env python3
"""
Qwen-Image model implementation
Supports negative prompts and uses true_cfg_scale with 50 steps optimal
"""

from typing import Dict, Optional, Tuple
import torch
from PIL import Image
from diffusers import QwenImagePipeline
from .base import BaseModel


class QwenImageModel(BaseModel):
    """Qwen-Image-2512 implementation"""

    def load_pipeline(self, progress_callback=None) -> str:
        """Load Qwen-Image pipeline"""
        if self.pipeline is not None:
            return "Model already loaded"

        try:
            if progress_callback:
                progress_callback(0, desc="Setting up device...")

            device, device_name = self.setup_device()

            if progress_callback:
                progress_callback(0.3, desc="Loading Qwen-Image pipeline...")

            # Qwen-Image is typically loaded from HuggingFace Hub
            # But also support local if path ends with .safetensors
            if self.model_path.endswith(".safetensors"):
                # Load from single file
                self.pipeline = QwenImagePipeline.from_single_file(
                    self.model_path,
                    torch_dtype=self.dtype,
                    low_cpu_mem_usage=False,
                )
            else:
                # Load from HuggingFace Hub
                self.pipeline = QwenImagePipeline.from_pretrained(
                    self.model_path,
                    torch_dtype=self.dtype,
                    low_cpu_mem_usage=False,
                )

            if progress_callback:
                progress_callback(0.7, desc="Enabling optimizations...")

            # Enable memory optimizations
            if device.type == "mps":
                self.pipeline.enable_sequential_cpu_offload(device=device)
                self.pipeline.enable_attention_slicing()
            elif device.type == "cuda":
                self.pipeline.enable_model_cpu_offload()
                self.pipeline.enable_attention_slicing()
            else:
                self.pipeline = self.pipeline.to(device)

            if progress_callback:
                progress_callback(1.0, desc="Model loaded successfully!")

            return f"Qwen-Image loaded on {device_name}"

        except Exception as e:
            return f"Error loading Qwen-Image: {e}"

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        progress_callback=None,
    ) -> Tuple[Image.Image, Dict]:
        """Generate image with Qwen-Image"""
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        # Use defaults from config
        steps = steps or self.default_steps
        guidance_scale = guidance_scale or self.default_guidance
        width = width or self.default_resolution
        height = height or self.default_resolution

        # Setup generator
        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        # Append LoRA prompt if applicable
        full_prompt = prompt
        lora_suffix = self.get_lora_prompt_suffix()
        if lora_suffix:
            full_prompt = f"{prompt}, {lora_suffix}"

        # Qwen-Image SUPPORTS negative prompts
        # Use a space as negative prompt if none provided (required for true_cfg_scale)
        if negative_prompt is None or not negative_prompt.strip():
            negative_prompt = " "

        # Prepare generation kwargs
        gen_kwargs = {
            "prompt": full_prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": steps,
            "height": height,
            "width": width,
            "generator": generator,
        }

        # Qwen uses true_cfg_scale instead of guidance_scale
        # Check pipeline signature to determine which parameter to use
        import inspect
        sig = inspect.signature(self.pipeline.__call__)
        if "true_cfg_scale" in sig.parameters:
            gen_kwargs["true_cfg_scale"] = guidance_scale
        elif "guidance_scale" in sig.parameters:
            gen_kwargs["guidance_scale"] = guidance_scale

        # Generate
        image = self.pipeline(**gen_kwargs).images[0]

        # Clear cache
        self.clear_cache()

        # Build metadata
        metadata = {
            "model": self.model_name,
            "prompt": full_prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "lora": self.current_lora["label"] if self.current_lora else None,
        }

        return image, metadata
