#!/usr/bin/env python3
"""
Generic SDXL model implementation
Supports full CFG guidance and negative prompts.
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

import torch
from diffusers import StableDiffusionXLPipeline
from .base import BaseModel
from .mixins import CLIPTokenLimitMixin


class SDXLModel(CLIPTokenLimitMixin, BaseModel):
    """Generic SDXL implementation (Juggernaut XL, DreamShaper XL, etc.)"""

    def _create_pipeline(self):
        """Load SDXL pipeline from HuggingFace"""
        return StableDiffusionXLPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
        )
