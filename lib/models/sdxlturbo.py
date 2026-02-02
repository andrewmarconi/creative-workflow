#!/usr/bin/env python3
"""
SDXL Turbo model implementation
Ultra-fast 1-step generation with guidance_scale=0.0
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

from typing import Dict, Optional, Tuple
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline
from .base import BaseModel


class SDXLTurboModel(BaseModel):
    """SDXL Turbo implementation"""

    def load_pipeline(self, progress_callback=None) -> str:
        """Load SDXL Turbo pipeline"""
        if self.pipeline is not None:
            return "Model already loaded"

        try:
            if progress_callback:
                progress_callback(0, desc="Setting up device...")

            device, device_name = self.setup_device()

            if progress_callback:
                progress_callback(0.3, desc="Loading SDXL Turbo pipeline...")

            self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
                variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
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

            return f"SDXL Turbo loaded on {device_name}"

        except Exception as e:
            return f"Error loading SDXL Turbo: {e}"

    def _fit_prompt_to_token_limit(self, prompt: str, suffix: str) -> str:
        """
        Build a prompt that fits within CLIP's 77-token limit.

        Prioritizes the LoRA suffix (trigger words) by reserving tokens for it,
        then fills remaining space with as much of the prompt as possible.
        Truncates from the end of the prompt text if needed.

        Args:
            prompt: The main prompt text
            suffix: LoRA trigger words to append

        Returns:
            Combined prompt that fits within 77 tokens
        """
        tokenizer = self.pipeline.tokenizer
        # 77 tokens total, minus 2 for BOS/EOS
        max_content_tokens = tokenizer.model_max_length - 2

        if not suffix:
            # No suffix — just truncate the prompt if needed
            tokens = tokenizer.encode(prompt, add_special_tokens=False)
            if len(tokens) <= max_content_tokens:
                return prompt
            truncated_tokens = tokens[:max_content_tokens]
            return tokenizer.decode(truncated_tokens, skip_special_tokens=True)

        # Reserve space for suffix
        suffix_with_sep = f", {suffix}"
        suffix_tokens = tokenizer.encode(suffix_with_sep, add_special_tokens=False)
        prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)

        total = len(prompt_tokens) + len(suffix_tokens)
        if total <= max_content_tokens:
            return f"{prompt}{suffix_with_sep}"

        # Truncate the prompt to fit
        available_for_prompt = max_content_tokens - len(suffix_tokens)
        if available_for_prompt <= 0:
            # Suffix alone exceeds limit — truncate suffix too
            truncated = tokenizer.decode(
                suffix_tokens[:max_content_tokens], skip_special_tokens=True
            )
            return truncated

        truncated_prompt = tokenizer.decode(
            prompt_tokens[:available_for_prompt], skip_special_tokens=True
        )
        print(f"DEBUG [SDXL Turbo]: Prompt truncated from {len(prompt_tokens)} to {available_for_prompt} tokens to fit 77-token CLIP limit")
        return f"{truncated_prompt}{suffix_with_sep}"

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
        """Generate image with SDXL Turbo"""
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        steps = steps or self.default_steps
        guidance_scale = self.default_guidance  # Always 0.0 for turbo
        width = width or self.default_resolution
        height = height or self.default_resolution

        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        # Build prompt that fits within CLIP's 77-token limit,
        # prioritizing LoRA trigger words
        lora_suffix = self.get_lora_prompt_suffix()
        full_prompt = self._fit_prompt_to_token_limit(prompt, lora_suffix)

        image = self.pipeline(
            prompt=full_prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
            generator=generator,
        ).images[0]

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
        }

        return image, metadata
