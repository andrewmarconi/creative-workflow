"""
Core models for LLM model management.

This module provides database models for tracking:
- LLM models (HuggingFace model IDs) used for text generation

Note: Geographic models (Region, Country, Language) have been relocated to cw.audiences.
"""

from django.db import models


class LLMModel(models.Model):
    """HuggingFace language model configuration.

    Stores model identifiers and metadata for LLMs used in adaptation tasks.
    Each model can be marked as primary or alternative for specific languages.

    Example:
        >>> model = LLMModel.objects.create(
        ...     model_id="Qwen/Qwen2.5-7B-Instruct",
        ...     name="Qwen 2.5 7B Instruct",
        ...     notes="Good multilingual support"
        ... )
    """

    model_id = models.CharField(
        max_length=200,
        unique=True,
        help_text="HuggingFace model ID (e.g., 'Qwen/Qwen2.5-7B-Instruct').",
    )
    name = models.CharField(
        max_length=100,
        help_text="Friendly display name (e.g., 'Qwen 2.5 7B').",
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about model capabilities, strengths, or limitations.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this model is available for use.",
    )
    load_in_4bit = models.BooleanField(
        default=False,
        help_text="Load model with 4-bit quantization (requires bitsandbytes).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_llmmodel"
        ordering = ["name"]
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"

    def __str__(self):
        return self.name
