#!/usr/bin/env python3
"""
SDXL Turbo model implementation
Ultra-fast 1-step generation with guidance_scale=0.0
Handles CLIP 77-token limit by prioritizing LoRA trigger words.
"""

from typing import Dict
import logging
import torch
from diffusers import StableDiffusionXLPipeline
from .base import BaseModel
from .mixins import CLIPTokenLimitMixin, DebugLoggingMixin

logger = logging.getLogger(__name__)


class SDXLTurboModel(CLIPTokenLimitMixin, DebugLoggingMixin, BaseModel):
    """SDXL Turbo implementation"""

    def _create_pipeline(self):
        """Load SDXL Turbo pipeline from HuggingFace"""
        return StableDiffusionXLPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            variant="fp16" if self.dtype in (torch.float16, torch.bfloat16) else None,
        )

    def _apply_device_optimizations(self) -> None:
        """Apply device optimizations with MPS VAE fix"""
        device = self.device

        # For MPS, keep VAE on device but force float32
        if device.type == "mps":
            if hasattr(self.pipeline, 'vae'):
                logger.info(f"[SDXL Turbo MPS Fix] Converting VAE to float32 (keeping on MPS)")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)

            # Move entire pipeline to MPS
            self.pipeline.to(device)
            self.pipeline.enable_attention_slicing()

            # Ensure VAE is still float32 after pipeline.to()
            if hasattr(self.pipeline, 'vae'):
                logger.info(f"[SDXL Turbo MPS Fix] Re-confirming VAE float32 after pipeline.to()")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
        else:
            # Non-MPS: use parent implementation
            super()._apply_device_optimizations()

    def _post_lora_load_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA loading"""
        # LoRA loading can change VAE dtype - restore float32
        if self.device.type == "mps" and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SDXL Turbo MPS Fix] Re-applying VAE float32 after LoRA load")
            logger.info(f"[SDXL Turbo MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SDXL Turbo MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")

    def _post_lora_unload_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA unloading"""
        # LoRA unloading can change VAE dtype - restore float32
        if self.device.type == "mps" and hasattr(self.pipeline, 'vae'):
            logger.info(f"[SDXL Turbo MPS Fix] Re-applying VAE float32 after LoRA unload")
            logger.info(f"[SDXL Turbo MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[SDXL Turbo MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")

    def _build_prompts(self, params: Dict) -> Dict:
        """Build prompts with token limiting and debug logging"""
        # Get original prompt token count for debug output
        lora_suffix = self.get_lora_prompt_suffix()
        if lora_suffix:
            original_tokens = len(self.pipeline.tokenizer.encode(params['prompt'], add_special_tokens=False))

        # Apply token limiting (from mixin)
        params = super()._build_prompts(params)

        # Debug output
        if lora_suffix and self.enable_debug_logging:
            tokenizer = self.pipeline.tokenizer
            max_content_tokens = tokenizer.model_max_length - 2
            suffix_tokens = len(tokenizer.encode(f", {lora_suffix}", add_special_tokens=False))
            available_for_prompt = max_content_tokens - suffix_tokens
            self._debug_print(f"Prompt truncated from {original_tokens} to {available_for_prompt} tokens to fit 77-token CLIP limit")

        token_count = len(self.pipeline.tokenizer.encode(params['prompt'], add_special_tokens=False))
        self._debug_print(f"Prompt sent to pipeline ({token_count} tokens): '{params['prompt']}'")

        return params
