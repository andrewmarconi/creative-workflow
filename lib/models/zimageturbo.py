#!/usr/bin/env python3
"""
Z-Image Turbo model implementation
Optimized for 8-9 step fast generation with guidance_scale=0.0
"""

from typing import Dict, Optional, Tuple
import torch
from PIL import Image
from diffusers import ZImagePipeline
from .base import BaseModel


class ZImageTurboModel(BaseModel):
    """Z-Image Turbo implementation"""

    def load_pipeline(self, progress_callback=None) -> str:
        """Load Z-Image Turbo pipeline"""
        if self.pipeline is not None:
            return "Model already loaded"

        try:
            if progress_callback:
                progress_callback(0, desc="Setting up device...")

            device, device_name = self.setup_device()

            if progress_callback:
                progress_callback(0.3, desc="Loading Z-Image Turbo pipeline...")

            # Load from HuggingFace Hub (recommended for Z-Image Turbo)
            # Note: Loading from split local .safetensors files (diffusion model,
            # text encoder, VAE) requires complex component assembly not well
            # supported by from_single_file(). Use HuggingFace for simplicity.
            self.pipeline = ZImagePipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
                low_cpu_mem_usage=False,
            )

            if progress_callback:
                progress_callback(0.7, desc="Enabling optimizations...")

            # Enable memory optimizations for Apple Silicon
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

            return f"Z-Image Turbo loaded on {device_name}"

        except Exception as e:
            return f"Error loading Z-Image Turbo: {e}"

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
        """Generate image with Z-Image Turbo"""
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        # Use defaults from config
        steps = steps or self.default_steps
        guidance_scale = self.default_guidance  # Always 0.0 for turbo
        width = width or self.default_resolution
        height = height or self.default_resolution

        # Setup generator
        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        # Append LoRA prompt if applicable
        full_prompt = prompt
        lora_suffix = self.get_lora_prompt_suffix()
        print(f"DEBUG [ZImageTurboModel]: LoRA suffix from get_lora_prompt_suffix(): '{lora_suffix}'")
        print(f"DEBUG [ZImageTurboModel]: current_lora = {self.current_lora}")
        if lora_suffix:
            full_prompt = f"{prompt}, {lora_suffix}"
            print(f"DEBUG [ZImageTurboModel]: Appended LoRA suffix to prompt")
        else:
            print(f"DEBUG [ZImageTurboModel]: No LoRA suffix to append")

        # Z-Image Turbo does NOT support negative prompts
        # Ignore negative_prompt parameter

        print(f"DEBUG [ZImageTurboModel]: Final prompt being sent to pipeline:")
        print(f"  '{full_prompt}'")

        # Generate
        image = self.pipeline(
            prompt=full_prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
            generator=generator,
            callback_on_step_end=self._create_step_callback(progress_callback, steps),
            callback_on_step_end_tensor_inputs=["latents"],
        ).images[0]

        # Clear cache
        self.clear_cache()

        # Build metadata
        metadata = {
            "model": self.model_name,
            "prompt": full_prompt,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "lora": self.current_lora["label"] if self.current_lora else None,
        }

        return image, metadata

    def _create_step_callback(self, progress_callback, total_steps):
        """Create callback for step-by-step progress updates"""
        if progress_callback is None:
            return None

        def callback(pipe, step_index, timestep, callback_kwargs):
            progress = (step_index + 1) / total_steps
            progress_callback(progress, desc=f"Step {step_index + 1}/{total_steps}")
            return callback_kwargs

        return callback
