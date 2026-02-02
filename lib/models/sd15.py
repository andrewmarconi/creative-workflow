#!/usr/bin/env python3
"""
Stable Diffusion 1.5 model implementation
Supports negative prompts and CLIP 77-token limit.
"""

import re
from typing import Dict, Optional, Tuple
import torch
from PIL import Image
from diffusers import StableDiffusionPipeline
from .base import BaseModel


class SD15Model(BaseModel):
    """Stable Diffusion 1.5 implementation (Realistic Vision, etc.)"""

    @staticmethod
    def _strip_a1111_lora_tags(text: str) -> str:
        """Remove A1111/ComfyUI <lora:...> tags which are meaningless in diffusers."""
        return re.sub(r'<lora:[^>]+>', '', text).strip().rstrip(',').strip()

    def _fit_prompt_to_token_limit(self, prompt: str, suffix: str) -> str:
        """
        Build a prompt that fits within CLIP's 77-token limit.
        Prioritizes the LoRA suffix (trigger words), then fills remaining
        space with as much of the prompt as possible.
        """
        suffix = self._strip_a1111_lora_tags(suffix)
        tokenizer = self.pipeline.tokenizer
        max_content_tokens = tokenizer.model_max_length - 2

        if not suffix:
            tokens = tokenizer.encode(prompt, add_special_tokens=False)
            if len(tokens) <= max_content_tokens:
                return prompt
            return tokenizer.decode(tokens[:max_content_tokens], skip_special_tokens=True)

        suffix_with_sep = f", {suffix}"
        suffix_tokens = tokenizer.encode(suffix_with_sep, add_special_tokens=False)
        prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)

        if len(prompt_tokens) + len(suffix_tokens) <= max_content_tokens:
            return f"{prompt}{suffix_with_sep}"

        available = max_content_tokens - len(suffix_tokens)
        if available <= 0:
            return tokenizer.decode(suffix_tokens[:max_content_tokens], skip_special_tokens=True)

        truncated = tokenizer.decode(prompt_tokens[:available], skip_special_tokens=True)
        return f"{truncated}{suffix_with_sep}"

    def load_pipeline(self, progress_callback=None) -> str:
        if self.pipeline is not None:
            return "Model already loaded"

        try:
            if progress_callback:
                progress_callback(0, desc="Setting up device...")
            device, device_name = self.setup_device()

            if progress_callback:
                progress_callback(0.3, desc=f"Loading {self.model_name} pipeline...")

            self.pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
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
        progress_callback=None,
    ) -> Tuple[Image.Image, Dict]:
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        steps = steps or self.default_steps
        guidance_scale = guidance_scale if guidance_scale is not None else self.default_guidance
        width = width or self.default_resolution
        height = height or self.default_resolution

        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        lora_suffix = self.get_lora_prompt_suffix()
        full_prompt = self._fit_prompt_to_token_limit(prompt, lora_suffix)

        gen_kwargs = {
            "prompt": full_prompt,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "height": height,
            "width": width,
            "generator": generator,
        }

        if self.supports_negative_prompt and negative_prompt:
            neg_suffix = self.get_lora_negative_prompt_suffix()
            full_negative = f"{negative_prompt}, {neg_suffix}" if neg_suffix else negative_prompt
            gen_kwargs["negative_prompt"] = full_negative

        image = self.pipeline(**gen_kwargs).images[0]
        self.clear_cache()

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
