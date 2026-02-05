#!/usr/bin/env python3
"""
Flux.1-dev model implementation
Uses distilled guidance (guidance_scale=3.5) with 28 steps optimal
"""

from diffusers import FluxPipeline

from .base import BaseModel


class FluxModel(BaseModel):
    """Flux.1-dev implementation"""

    def _create_pipeline(self):
        """Load Flux.1-dev pipeline from HuggingFace"""
        return FluxPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=False,
        )
