#!/usr/bin/env python3
"""
Stable Diffusion 1.5 model implementation
Supports full CFG guidance and negative prompts.
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

from diffusers import StableDiffusionPipeline
from .base import BaseModel
from .mixins import CLIPTokenLimitMixin


class SD15Model(CLIPTokenLimitMixin, BaseModel):
    """Stable Diffusion 1.5 implementation (Realistic Vision, etc.)"""

    def _create_pipeline(self):
        """Load SD 1.5 pipeline from HuggingFace"""
        return StableDiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
        )
