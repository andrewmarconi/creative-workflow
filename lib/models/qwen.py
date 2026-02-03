#!/usr/bin/env python3
"""
Qwen-Image model implementation
Supports negative prompts and uses true_cfg_scale with 50 steps optimal
"""

from typing import Dict
import logging
import inspect
from diffusers import QwenImagePipeline
from .base import BaseModel

logger = logging.getLogger(__name__)


class QwenImageModel(BaseModel):
    """Qwen-Image-2512 implementation"""

    def _create_pipeline(self):
        """Load Qwen-Image pipeline with optional 8-bit quantization"""
        load_kwargs = {
            'torch_dtype': self.dtype,
            'low_cpu_mem_usage': True,
            'use_safetensors': True,
        }

        # Add 8-bit quantization if enabled
        if self.settings.get("load_in_8bit", False):
            load_kwargs['load_in_8bit'] = True
            load_kwargs['device_map'] = 'auto'

        return QwenImagePipeline.from_pretrained(self.model_path, **load_kwargs)

    def _apply_device_optimizations(self) -> None:
        """Apply optimizations with VAE slicing"""
        super()._apply_device_optimizations()

        # Enable VAE slicing for lower memory
        if hasattr(self.pipeline, 'vae'):
            self.pipeline.vae.enable_slicing()

    def _handle_special_prompt_requirements(self, params: Dict) -> Dict:
        """Qwen requires space for empty negative prompt"""
        if params['negative_prompt'] is None or not params['negative_prompt'].strip():
            params['negative_prompt'] = " "
        return params

    def _build_pipeline_kwargs(self, params: Dict, progress_callback) -> Dict:
        """Build kwargs with runtime parameter detection"""
        gen_kwargs = super()._build_pipeline_kwargs(params, progress_callback)

        # Detect true_cfg_scale vs guidance_scale at runtime
        sig = inspect.signature(self.pipeline.__call__)
        if 'true_cfg_scale' in sig.parameters:
            gen_kwargs['true_cfg_scale'] = gen_kwargs.pop('guidance_scale')

        # Add progress callback if supported
        if progress_callback and 'callback_on_step_end' in sig.parameters:
            gen_kwargs['callback_on_step_end'] = progress_callback
            if 'callback_on_step_end_tensor_inputs' in sig.parameters:
                gen_kwargs['callback_on_step_end_tensor_inputs'] = ['latents']

        logger.info(f"Starting inference with {params['steps']} steps")
        logger.info(f"Generation kwargs keys: {list(gen_kwargs.keys())}")

        return gen_kwargs
