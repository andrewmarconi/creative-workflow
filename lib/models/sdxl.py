#!/usr/bin/env python3
"""
Generic SDXL model implementation
Supports full CFG guidance and negative prompts.
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

import logging
import torch
from diffusers import StableDiffusionXLPipeline
from .base import BaseModel
from .mixins import CLIPTokenLimitMixin

logger = logging.getLogger(__name__)


class SDXLModel(CLIPTokenLimitMixin, BaseModel):
    """Generic SDXL implementation (Juggernaut XL, DreamShaper XL, etc.)"""

    def _create_pipeline(self):
        """Load SDXL pipeline from HuggingFace"""
        return StableDiffusionXLPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
        )

    def _apply_device_optimizations(self) -> None:
        """Apply device optimizations with MPS VAE fix"""
        # Use base implementation (keeps VAE on MPS in float32)
        super()._apply_device_optimizations()

    def _post_lora_load_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA loading"""
        # LoRA loading can change VAE dtype - restore float32
        if self.device.type == 'mps' and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SDXL MPS Fix] Re-applying VAE float32 after LoRA load")
            logger.info(f"[SDXL MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SDXL MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")

    def _post_lora_unload_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA unloading"""
        # LoRA unloading can change VAE dtype - restore float32
        if self.device.type == 'mps' and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SDXL MPS Fix] Re-applying VAE float32 after LoRA unload")
            logger.info(f"[SDXL MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SDXL MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")
