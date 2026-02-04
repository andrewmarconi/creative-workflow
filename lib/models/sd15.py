#!/usr/bin/env python3
"""
Stable Diffusion 1.5 model implementation
Supports full CFG guidance and negative prompts.
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

import logging
import torch
from diffusers import StableDiffusionPipeline
from .base import BaseModel
from .mixins import CLIPTokenLimitMixin

logger = logging.getLogger(__name__)


class SD15Model(CLIPTokenLimitMixin, BaseModel):
    """Stable Diffusion 1.5 implementation (Realistic Vision, etc.)"""

    def _create_pipeline(self):
        """Load SD 1.5 pipeline from HuggingFace"""
        return StableDiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
        )

    def _apply_device_optimizations(self) -> None:
        """Apply device optimizations with MPS VAE fix"""
        # Use base implementation (keeps VAE on MPS in float32)
        super()._apply_device_optimizations()

    def _post_lora_load_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA loading"""
        # LoRA loading can change VAE dtype - restore float32
        if self.device.type == 'mps' and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SD15 MPS Fix] Re-applying VAE float32 after LoRA load")
            logger.info(f"[SD15 MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SD15 MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")

    def _post_lora_unload_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA unloading"""
        # LoRA unloading can change VAE dtype - restore float32
        if self.device.type == 'mps' and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SD15 MPS Fix] Re-applying VAE float32 after LoRA unload")
            logger.info(f"[SD15 MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SD15 MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")
