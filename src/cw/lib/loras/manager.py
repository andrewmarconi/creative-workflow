#!/usr/bin/env python3
"""
LoRA Manager for Creative Workflow
Handles LoRA filtering, loading, and compatibility checking
"""

from pathlib import Path
from typing import Dict, List, Optional

from config import get_config


class LoRAManager:
    """Manages LoRA adapters and their compatibility with models"""

    def __init__(self):
        self.config = get_config()
        self.base_model_path = self.config.base_model_path

    def get_compatible_loras(self, model_slug: str) -> List[Dict]:
        """
        Get list of LoRAs compatible with specified model

        Args:
            model_slug: Model slug (e.g., "zimageturbo", "flux1_dev")

        Returns:
            List of compatible LoRA configurations
        """
        return self.config.get_loras_for_model(model_slug)

    def get_lora_choices(self, model_slug: str) -> List[str]:
        """
        Get list of LoRA labels for UI dropdown, filtered by model compatibility

        Args:
            model_slug: Model slug to filter by

        Returns:
            List of LoRA labels, starting with "None (No LoRA)"
        """
        choices = ["None (No LoRA)"]
        compatible_loras = self.get_compatible_loras(model_slug)

        for lora in compatible_loras:
            choices.append(lora["label"])

        return choices

    def get_lora_by_label(self, label: str, model_slug: Optional[str] = None) -> Optional[Dict]:
        """
        Get LoRA configuration by label

        Args:
            label: LoRA label to search for
            model_slug: Optional model slug to filter by

        Returns:
            LoRA configuration dict or None
        """
        if label == "None (No LoRA)":
            return None

        loras = self.get_compatible_loras(model_slug) if model_slug else self.config.get_loras()

        for lora in loras:
            if lora["label"] == label:
                return lora

        return None

    def get_lora_path(self, lora_config: Dict) -> str:
        """
        Get full path to LoRA file

        Args:
            lora_config: LoRA configuration from presets

        Returns:
            Full path to LoRA .safetensors file
        """
        lora_path = lora_config["path"]

        # LoRAs are stored relative to base_model_path
        full_path = self.base_model_path / lora_path

        return str(full_path)

    def validate_lora_exists(self, lora_config: Dict) -> bool:
        """
        Check if LoRA file exists

        Args:
            lora_config: LoRA configuration from presets

        Returns:
            True if file exists, False otherwise
        """
        lora_path = self.get_lora_path(lora_config)
        return Path(lora_path).exists()

    def get_lora_strength(self, lora_config: Dict) -> float:
        """
        Get recommended strength for LoRA

        Args:
            lora_config: LoRA configuration from presets

        Returns:
            LoRA strength (default 1.0)
        """
        return lora_config.get("settings", {}).get("strength", 1.0)

    def get_lora_prompt_suffix(self, lora_config: Dict) -> str:
        """
        Get prompt suffix for LoRA

        Args:
            lora_config: LoRA configuration from presets

        Returns:
            Prompt suffix string
        """
        return lora_config.get("prompt", "")

    def is_compatible(self, lora_config: Dict, model_slug: str) -> bool:
        """
        Check if LoRA is compatible with model

        Args:
            lora_config: LoRA configuration from presets
            model_slug: Model slug to check compatibility with

        Returns:
            True if compatible, False otherwise
        """
        compatibility = lora_config.get("compatibility", [])
        return model_slug in compatibility
