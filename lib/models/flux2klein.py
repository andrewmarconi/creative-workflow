#!/usr/bin/env python3
"""
Flux.2 Klein 4B model implementation
Distilled model optimized for fast generation (4 steps, guidance_scale=1.0)
"""

from typing import Dict, Optional, Tuple
import torch
from PIL import Image
from diffusers import Flux2KleinPipeline
from .base import BaseModel


class Flux2KleinModel(BaseModel):
    """Flux.2 Klein 4B implementation"""

    def load_pipeline(self, progress_callback=None) -> str:
        """Load Flux.2 Klein pipeline"""
        if self.pipeline is not None:
            return "Model already loaded"

        try:
            if progress_callback:
                progress_callback(0, desc="Setting up device...")

            device, device_name = self.setup_device()

            if progress_callback:
                progress_callback(0.3, desc="Loading Flux.2 Klein pipeline...")

            self.pipeline = Flux2KleinPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
                low_cpu_mem_usage=False,
            )

            if progress_callback:
                progress_callback(0.7, desc="Enabling optimizations...")

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

            return f"Flux.2 Klein 4B loaded on {device_name}"

        except Exception as e:
            return f"Error loading Flux.2 Klein: {e}"

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
        """Generate image with Flux.2 Klein"""
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        steps = steps or self.default_steps
        guidance_scale = guidance_scale if guidance_scale is not None else self.default_guidance
        width = width or self.default_resolution
        height = height or self.default_resolution

        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        full_prompt = prompt
        lora_suffix = self.get_lora_prompt_suffix()
        if lora_suffix:
            full_prompt = f"{prompt}, {lora_suffix}"

        gen_kwargs = {
            "prompt": full_prompt,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "height": height,
            "width": width,
            "generator": generator,
        }

        if self.max_sequence_length is not None:
            gen_kwargs["max_sequence_length"] = self.max_sequence_length

        image = self.pipeline(**gen_kwargs).images[0]

        self.clear_cache()

        metadata = {
            "model": self.model_name,
            "prompt": full_prompt,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "seed": seed,
            "lora": self.current_lora["label"] if self.current_lora else None,
            "max_sequence_length": self.max_sequence_length,
        }

        return image, metadata
