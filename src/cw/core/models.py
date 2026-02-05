"""
Core models for language and LLM model management.

This module provides database models for tracking:
- LLM models (HuggingFace model IDs) used for text generation
- Languages with their recommended LLM models for adaptations
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_llmmodel"
        ordering = ["name"]
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"

    def __str__(self):
        return self.name


class Language(models.Model):
    """Language configuration with LLM model recommendations.

    Each language has a primary model recommendation and optional alternatives.
    Used by the adaptation system to select the best model for generating
    culturally-adapted content.

    Example:
        >>> japanese = Language.objects.create(
        ...     code="ja",
        ...     name="Japanese",
        ...     primary_model=qwen_model,
        ...     notes="Qwen best, avoid Mistral"
        ... )
        >>> japanese.alternative_models.add(aya_model)
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO 639-1 language code (e.g., 'ja', 'de', 'es-MX').",
    )
    name = models.CharField(
        max_length=100,
        help_text="Language name (e.g., 'Japanese', 'German').",
    )
    primary_model = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="primary_for_languages",
        help_text="Recommended model for this language.",
    )
    alternative_models = models.ManyToManyField(
        LLMModel,
        blank=True,
        related_name="alternative_for_languages",
        help_text="Alternative models that can also handle this language.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about language-specific considerations.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this language is available for adaptations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_language"
        ordering = ["name"]
        verbose_name = "Language"
        verbose_name_plural = "Languages"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_all_models(self):
        """Get primary model plus all alternatives as a queryset."""
        return LLMModel.objects.filter(
            models.Q(pk=self.primary_model_id) | models.Q(alternative_for_languages=self)
        ).distinct()
