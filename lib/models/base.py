#!/usr/bin/env python3
"""
Base model class for Creative Workflow
Abstract base class that all model implementations inherit from
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
from PIL import Image


class BaseModel(ABC):
    """Abstract base class for all diffusion models"""

    def __init__(self, model_config: Dict, model_path: str):
        """
        Initialize base model

        Args:
            model_config: Model configuration from presets.json
            model_path: Full path to model file or HuggingFace ID
        """
        self.config = model_config
        self.model_path = model_path
        self.pipeline = None
        self.device = None
        self.current_lora = None

        # Extract settings
        self.settings = model_config.get("settings", {})
        self.default_steps = self.settings.get("steps", 20)
        self.default_guidance = self.settings.get("guidance_scale", 7.5)
        self.default_resolution = self.settings.get("resolution", 1024)
        self.supports_negative_prompt = self.settings.get("supports_negative_prompt", False)
        self.max_sequence_length = self.settings.get("max_sequence_length")

        # Get dtype — FP8 variants can't be used as torch_dtype for loading,
        # so fall back to bfloat16 (weights are upcast automatically).
        dtype_str = self.settings.get("dtype", "bfloat16")
        if dtype_str.startswith("float8"):
            self.dtype = torch.bfloat16
        else:
            self.dtype = getattr(torch, dtype_str, torch.bfloat16)

    @abstractmethod
    def load_pipeline(self, progress_callback=None) -> str:
        """
        Load the diffusion pipeline

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Status message
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        progress_callback=None,
    ) -> Tuple[Image.Image, Dict]:
        """
        Generate an image

        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt (if supported)
            steps: Number of inference steps
            guidance_scale: Guidance scale
            width: Image width
            height: Image height
            seed: Random seed
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (generated image, metadata dict)
        """
        pass

    def setup_device(self) -> Tuple[torch.device, str]:
        """
        Configure device for Apple Silicon optimization

        Returns:
            Tuple of (device, device_name)
        """
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            device_name = "MPS (Apple Silicon)"
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            device_name = "CUDA"
        else:
            device = torch.device("cpu")
            device_name = "CPU"

        self.device = device
        return device, device_name

    def load_lora(self, lora_path: str, lora_config: Dict) -> str:
        """
        Load a LoRA adapter

        Args:
            lora_path: Path to LoRA file
            lora_config: LoRA configuration from presets

        Returns:
            Status message
        """
        if self.pipeline is None:
            return "Error: Model not loaded yet"

        try:
            # Unload previous LoRA if any
            if self.current_lora is not None:
                try:
                    self.pipeline.unload_lora_weights()
                except Exception:
                    pass

            # Load new LoRA
            if not Path(lora_path).exists():
                return f"Error: LoRA file not found: {lora_path}"

            # Get LoRA strength from settings
            strength = lora_config.get("settings", {}).get("strength", 1.0)

            # Load LoRA weights
            self.pipeline.load_lora_weights(lora_path, adapter_name="default")

            # Set LoRA scale if applicable
            if hasattr(self.pipeline, "set_adapters"):
                self.pipeline.set_adapters(["default"], adapter_weights=[strength])

            self.current_lora = lora_config

            return f"LoRA loaded: {lora_config['label']} (strength: {strength})"

        except Exception as e:
            return f"Error loading LoRA: {e}"

    def unload_lora(self) -> str:
        """
        Unload current LoRA

        Returns:
            Status message
        """
        if self.pipeline is None:
            return "Error: Model not loaded yet"

        if self.current_lora is None:
            return "No LoRA loaded"

        try:
            self.pipeline.unload_lora_weights()
            self.current_lora = None
            return "LoRA unloaded"
        except Exception:
            self.current_lora = None
            return "LoRA reset"

    def get_lora_prompt_suffix(self) -> str:
        """Get prompt suffix from current LoRA"""
        if self.current_lora is None:
            return ""
        return self.current_lora.get("prompt", "")

    def get_lora_negative_prompt_suffix(self) -> str:
        """Get negative prompt suffix from current LoRA"""
        if self.current_lora is None:
            return ""
        return self.current_lora.get("negative_prompt", "")

    def clear_cache(self) -> None:
        """Clear GPU memory cache"""
        if self.device is None:
            return

        if self.device.type == "mps":
            torch.mps.empty_cache()
        elif self.device.type == "cuda":
            torch.cuda.empty_cache()

    def is_loaded(self) -> bool:
        """Check if pipeline is loaded"""
        return self.pipeline is not None

    @property
    def model_name(self) -> str:
        """Get model label"""
        return self.config.get("label", "Unknown Model")

    @property
    def model_slug(self) -> str:
        """Get model slug"""
        return self.config.get("slug", "unknown")
