#!/usr/bin/env python3
"""
SDXL ControlNet model implementation.

Combines a StableDiffusionXL base model with a ControlNet conditioning model
to generate images guided by structural control signals (edges, depth, line art).
"""

import logging

import torch
from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline

from .base import BaseModel
from .mixins import CompelPromptMixin

logger = logging.getLogger(__name__)


class SDXLControlNetModel(CompelPromptMixin, BaseModel):
    """SDXL + ControlNet implementation for structure-guided generation."""

    def __init__(self, model_config: dict, model_path: str):
        super().__init__(model_config, model_path)
        self.controlnet_path = self.settings.get("controlnet_path", "")

    def _create_pipeline(self):
        """Load SDXL pipeline with ControlNet."""
        logger.info(f"Loading ControlNet from: {self.controlnet_path}")
        controlnet = ControlNetModel.from_pretrained(
            self.controlnet_path,
            torch_dtype=self.dtype,
            variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
        )

        logger.info(f"Loading SDXL base model from: {self.model_path}")
        return StableDiffusionXLControlNetPipeline.from_pretrained(
            self.model_path,
            controlnet=controlnet,
            torch_dtype=self.dtype,
            variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
        )

    def _build_pipeline_kwargs(self, params, progress_callback):
        """Add ControlNet-specific kwargs (control image, conditioning scale)."""
        kwargs = super()._build_pipeline_kwargs(params, progress_callback)

        # Inject the preprocessed control image
        if "control_image" in params:
            kwargs["image"] = params["control_image"]

        # ControlNet conditioning parameters
        if "conditioning_scale" in params:
            kwargs["controlnet_conditioning_scale"] = params["conditioning_scale"]
        if "guidance_end" in params:
            kwargs["control_guidance_end"] = params["guidance_end"]

        return kwargs

    def _build_metadata(self, params):
        """Add ControlNet info to generation metadata."""
        metadata = super()._build_metadata(params)
        metadata["controlnet"] = {
            "path": self.controlnet_path,
            "conditioning_scale": params.get("conditioning_scale"),
            "guidance_end": params.get("guidance_end"),
        }
        return metadata

    def _post_lora_load_fixes(self):
        """Re-apply MPS VAE fix after LoRA loading."""
        if self.device and self.device.type == "mps" and hasattr(self.pipeline, "vae"):
            logger.info("[SDXL-CN MPS Fix] Re-applying VAE float32 after LoRA load")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)

    def _post_lora_unload_fixes(self):
        """Re-apply MPS VAE fix after LoRA unloading."""
        if self.device and self.device.type == "mps" and hasattr(self.pipeline, "vae"):
            logger.info("[SDXL-CN MPS Fix] Re-applying VAE float32 after LoRA unload")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
