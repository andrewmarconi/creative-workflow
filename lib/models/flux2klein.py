#!/usr/bin/env python3
"""
Flux.2 Klein 4B model implementation
Distilled model optimized for fast generation (4 steps, guidance_scale=1.0)
"""

from diffusers import Flux2KleinPipeline
from .base import BaseModel


class Flux2KleinModel(BaseModel):
    """Flux.2 Klein 4B implementation"""

    def _create_pipeline(self):
        """Load Flux.2 Klein pipeline from HuggingFace"""
        return Flux2KleinPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
            low_cpu_mem_usage=False,
        )
