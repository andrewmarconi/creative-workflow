"""
Creative Workflow - Model Implementations
Modular model classes for different diffusion pipelines
"""

from .base import BaseModel
from .mixins import CLIPTokenLimitMixin, CompelPromptMixin, DebugLoggingMixin
from .zimageturbo import ZImageTurboModel
from .flux import FluxModel
from .qwen import QwenImageModel
from .sdxlturbo import SDXLTurboModel
from .sdxl import SDXLModel
from .sd15 import SD15Model


class ModelFactory:
    """Factory for creating model instances based on pipeline type"""

    @staticmethod
    def create_model(model_config: dict, model_path: str) -> BaseModel:
        """
        Create model instance based on pipeline type

        Args:
            model_config: Model configuration from presets
            model_path: Full path to model or HuggingFace ID

        Returns:
            Model instance
        """
        pipeline_name = model_config.get("pipeline", "")

        if pipeline_name == "ZImagePipeline":
            return ZImageTurboModel(model_config, model_path)
        elif pipeline_name == "FluxPipeline":
            return FluxModel(model_config, model_path)
        elif pipeline_name == "QwenImagePipeline":
            return QwenImageModel(model_config, model_path)
        elif pipeline_name == "AutoPipelineForText2Image":
            return SDXLTurboModel(model_config, model_path)
        elif pipeline_name == "StableDiffusionXLPipeline":
            return SDXLModel(model_config, model_path)
        elif pipeline_name == "StableDiffusionPipeline":
            return SD15Model(model_config, model_path)
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_name}")


__all__ = [
    "BaseModel",
    "CLIPTokenLimitMixin",
    "CompelPromptMixin",
    "DebugLoggingMixin",
    "ZImageTurboModel",
    "FluxModel",
    "QwenImageModel",
    "SDXLTurboModel",
    "SDXLModel",
    "SD15Model",
    "ModelFactory",
]
