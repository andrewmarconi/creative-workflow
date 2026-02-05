#!/usr/bin/env python3
"""
Z-Image Turbo model implementation
Optimized for 8-9 step fast generation with guidance_scale=0.0
"""

import logging
from typing import Dict

import torch
from diffusers import ZImagePipeline

from .base import BaseModel
from .mixins import DebugLoggingMixin

logger = logging.getLogger(__name__)


class ZImageTurboModel(DebugLoggingMixin, BaseModel):
    """Z-Image Turbo implementation"""

    def _create_pipeline(self):
        """Load Z-Image Turbo pipeline from HuggingFace"""
        return ZImagePipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=False,
        )

    def _apply_device_optimizations(self) -> None:
        """Apply Z-Image specific optimizations"""
        device = self.device

        if device.type == "mps":
            # Keep VAE on device but force float32
            if hasattr(self.pipeline, "vae"):
                logger.info(f"[Z-Image MPS Fix] Converting VAE to float32 (keeping on MPS)")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)

            # Move entire pipeline to MPS
            self.pipeline.to(device)
            self.pipeline.enable_attention_slicing()

            # Ensure VAE is still float32 after pipeline.to()
            if hasattr(self.pipeline, "vae"):
                logger.info(f"[Z-Image MPS Fix] Re-confirming VAE float32 after pipeline.to()")
                self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
        elif device.type == "cuda":
            self.pipeline.enable_sequential_cpu_offload(device=device)
            self.pipeline.enable_attention_slicing()
            self.pipeline.enable_vae_slicing()
        else:
            self.pipeline = self.pipeline.to(device)

    def _build_prompts(self, params: Dict) -> Dict:
        """Build prompts with debug logging"""
        lora_suffix = self.get_lora_prompt_suffix()
        self._debug_print(f"LoRA suffix from get_lora_prompt_suffix(): '{lora_suffix}'")
        self._debug_print(f"current_lora = {self.current_lora}")

        if lora_suffix:
            params["prompt"] = f"{params['prompt']}, {lora_suffix}"
            self._debug_print("Appended LoRA suffix to prompt")
        else:
            self._debug_print("No LoRA suffix to append")

        self._debug_print(f"Final prompt being sent to pipeline: '{params['prompt']}'")
        return params

    def _build_pipeline_kwargs(self, params: Dict, progress_callback) -> Dict:
        """Build kwargs with step callback support"""
        gen_kwargs = super()._build_pipeline_kwargs(params, progress_callback)

        # Add step callback for progress tracking
        if progress_callback:
            gen_kwargs["callback_on_step_end"] = self._create_step_callback(
                progress_callback, params["steps"]
            )
            gen_kwargs["callback_on_step_end_tensor_inputs"] = ["latents"]

        return gen_kwargs

    def _create_step_callback(self, progress_callback, total_steps):
        """Create callback for step-by-step progress updates"""

        def callback(pipe, step_index, timestep, callback_kwargs):
            progress = (step_index + 1) / total_steps
            progress_callback(progress, desc=f"Step {step_index + 1}/{total_steps}")
            return callback_kwargs

        return callback

    def _post_lora_load_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA loading"""
        if self.device.type == "mps" and hasattr(self.pipeline, "vae"):
            logger.info(f"[Z-Image MPS Fix] Re-applying VAE float32 after LoRA load")
            logger.info(f"[Z-Image MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[Z-Image MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")

    def _post_lora_unload_fixes(self) -> None:
        """Re-apply MPS VAE fix after LoRA unloading"""
        if self.device.type == "mps" and hasattr(self.pipeline, "vae"):
            logger.info(f"[Z-Image MPS Fix] Re-applying VAE float32 after LoRA unload")
            logger.info(f"[Z-Image MPS Fix] VAE dtype before: {self.pipeline.vae.dtype}")
            self.pipeline.vae = self.pipeline.vae.to(dtype=torch.float32)
            logger.info(f"[Z-Image MPS Fix] VAE dtype after: {self.pipeline.vae.dtype}")
