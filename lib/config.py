#!/usr/bin/env python3
"""
Configuration loader and validator for QueerChaos 2
Loads presets.json and provides access to model and LoRA configurations
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class PresetsConfig:
    """Loads and validates presets.json configuration"""

    def __init__(self, presets_path: str = "presets.json"):
        self.presets_path = Path(presets_path)
        self._config = None
        self.load()

    def load(self) -> None:
        """Load presets from JSON file"""
        if not self.presets_path.exists():
            raise FileNotFoundError(f"Presets file not found: {self.presets_path}")

        try:
            with open(self.presets_path, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in presets file: {e}")

        # Validate structure
        self._validate()

    def _validate(self) -> None:
        """Validate presets structure"""
        if not isinstance(self._config, dict):
            raise ValueError("Presets must be a JSON object")

        if "config" not in self._config:
            raise ValueError("Missing 'config' section in presets")

        if "models" not in self._config:
            raise ValueError("Missing 'models' section in presets")

        if "loras" not in self._config:
            raise ValueError("Missing 'loras' section in presets")

    @property
    def base_model_path(self) -> Path:
        """Get base path for model files"""
        return Path(self._config["config"]["base_model_path"])

    @property
    def base_output_path(self) -> Path:
        """Get base path for output files"""
        return Path(self._config["config"]["base_output_path"])

    def get_models(self) -> List[Dict]:
        """Get list of all available models"""
        return self._config["models"]

    def get_model_by_slug(self, slug: str) -> Optional[Dict]:
        """Get model configuration by slug"""
        for model in self.get_models():
            if model["slug"] == slug:
                return model
        return None

    def get_loras(self) -> List[Dict]:
        """Get list of all available LoRAs"""
        return self._config["loras"]

    def get_loras_for_model(self, model_slug: str) -> List[Dict]:
        """Get LoRAs compatible with specified model"""
        compatible_loras = []
        for lora in self.get_loras():
            if model_slug in lora.get("compatibility", []):
                compatible_loras.append(lora)
        return compatible_loras

    def get_model_choices(self) -> List[str]:
        """Get list of model labels for UI dropdown"""
        return [model["label"] for model in self.get_models()]

    def get_model_by_label(self, label: str) -> Optional[Dict]:
        """Get model configuration by label"""
        for model in self.get_models():
            if model["label"] == label:
                return model
        return None

    def is_huggingface_model(self, model: Dict) -> bool:
        """Check if model path is a HuggingFace Hub ID"""
        path = model["path"]
        # Check for "Hugginface:" prefix or standard HF format "org/model"
        return path.startswith("Hugginface:") or path.startswith("Huggingface:") or (
            "/" in path and not path.endswith(".safetensors")
        )

    def get_model_path(self, model: Dict) -> str:
        """Get full model path (local or HuggingFace ID)"""
        path = model["path"]

        # If it's a HuggingFace model, strip the prefix
        if path.startswith("Hugginface:") or path.startswith("Huggingface:"):
            return path.split(":", 1)[1]

        # If it's a HuggingFace-style ID without prefix, return as-is
        if "/" in path and not path.endswith(".safetensors"):
            return path

        # Otherwise, it's a local path relative to base_model_path
        return str(self.base_model_path / path)


# Global config instance
_config_instance: Optional[PresetsConfig] = None


def get_config() -> PresetsConfig:
    """Get or create global config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = PresetsConfig()
    return _config_instance
