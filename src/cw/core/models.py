"""
Core models for LLM model management.

This module provides database models for tracking:
- LLM models (HuggingFace model IDs) used for text generation
- Prompt templates (Jinja2 templates for LLM prompts)

Note: Geographic models (Region, Country, Language) have been relocated to cw.audiences.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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


class PromptTemplate(models.Model):
    """Database-backed LLM prompt template with versioning and validation."""

    # Template categories
    CATEGORY_CHOICES = [
        ("enhancement", "Prompt Enhancement"),
        ("adaptation", "Cultural Adaptation"),
        ("evaluation", "Quality Evaluation"),
        ("concept", "Concept Analysis"),
    ]

    # Identity
    slug = models.SlugField(
        max_length=100,
        db_index=True,
        help_text="Template identifier (e.g., 'adaptation', 'concept-extraction')",
    )
    name = models.CharField(
        max_length=200, help_text="Human-readable name (e.g., 'Cultural Adaptation')"
    )

    # Categorization
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, help_text="Template category"
    )

    # Template Content
    template = models.TextField(help_text="Jinja2 template content")

    # Schema/Variables (optional metadata for validation)
    expected_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Expected template variables: {name: {type, required, description}}",
    )

    # Versioning
    version = models.PositiveIntegerField(
        default=1, help_text="Template version number (auto-incremented on save)"
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this version is the active version"
    )

    # Documentation
    description = models.TextField(blank=True, help_text="Purpose and usage notes")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_prompt_templates",
        help_text="User who created this template version",
    )

    # Analytics
    usage_count = models.PositiveIntegerField(
        default=0, help_text="Number of times this template has been rendered"
    )
    last_used_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time this template was rendered"
    )

    class Meta:
        db_table = "core_prompttemplate"
        constraints = [
            # Each slug+version combination must be unique
            models.UniqueConstraint(
                fields=["slug", "version"], name="unique_slug_version"
            ),
            # Only one active version per slug
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(is_active=True),
                name="unique_active_slug"
            ),
        ]
        ordering = ["-version", "slug"]
        indexes = [
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["category"]),
        ]
        verbose_name = "Prompt Template"
        verbose_name_plural = "Prompt Templates"

    def __str__(self):
        active_indicator = " [ACTIVE]" if self.is_active else ""
        return f"{self.name} (v{self.version}){active_indicator}"

    def clean(self):
        """Validate Jinja2 syntax on save."""
        from jinja2 import Environment, TemplateSyntaxError

        env = Environment(trim_blocks=True, lstrip_blocks=True)
        try:
            env.from_string(self.template)
        except TemplateSyntaxError as e:
            raise ValidationError(
                {"template": f"Invalid Jinja2 syntax: {e.message} at line {e.lineno}"}
            )

    def save(self, *args, **kwargs):
        """
        Save the template, auto-incrementing version if template content changed.

        If this is an update to an existing template and the template content
        has changed, we:
        1. Deactivate the old version
        2. Create a new version (incrementing version number)
        3. Mark it as active
        """
        # Check if this is an update to existing template with changed content
        if self.pk:
            try:
                old_version = self.__class__.objects.get(pk=self.pk)
                if old_version.template != self.template:
                    # Template changed - create new version
                    # Deactivate all other versions of this slug
                    self.__class__.objects.filter(slug=self.slug, is_active=True).update(
                        is_active=False
                    )
                    # Get highest version number for this slug
                    max_version = (
                        self.__class__.objects.filter(slug=self.slug).aggregate(
                            models.Max("version")
                        )["version__max"]
                        or 0
                    )
                    # Create new version
                    self.pk = None  # Force creation of new record
                    self.version = max_version + 1
                    self.is_active = True
            except self.__class__.DoesNotExist:
                pass

        # Run Jinja2 validation
        self.full_clean()

        super().save(*args, **kwargs)

    def render(self, **context):
        """
        Render this template with the provided context.

        Args:
            **context: Variables to pass to the Jinja2 template

        Returns:
            Rendered template string

        Updates usage analytics (usage_count, last_used_at).
        """
        from jinja2 import Environment

        env = Environment(trim_blocks=True, lstrip_blocks=True)
        template = env.from_string(self.template)

        # Update usage analytics (using F() to avoid race conditions)
        self.__class__.objects.filter(pk=self.pk).update(
            usage_count=models.F("usage_count") + 1, last_used_at=timezone.now()
        )

        return template.render(**context)
