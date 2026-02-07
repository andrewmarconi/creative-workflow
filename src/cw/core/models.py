"""
Core models for language and LLM model management.

This module provides database models for tracking:
- LLM models (HuggingFace model IDs) used for text generation
- Languages with their recommended LLM models for adaptations
- Regions and Countries for multi-dimensional adaptation context
- Compositional insights at each level (Region → Country → Language)
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


class Region(models.Model):
    """Cultural/market grouping with regional insights.

    Examples: North America, Nordics, DACH, LATAM

    Regional insights capture broad cultural patterns that apply across
    multiple countries in the region (e.g., Nordic minimalism, North American
    directness).
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code (e.g., 'NA', 'NORDICS', 'DACH')",
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'North America')",
    )
    description = models.TextField(
        blank=True,
        help_text="Region description and scope",
    )
    insights = models.JSONField(
        default=list,
        help_text="Regional cultural patterns: [{heading, points[]}]",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_region"
        ordering = ["name"]
        verbose_name = "Region"
        verbose_name_plural = "Regions"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def insights_as_markdown(self) -> str:
        """Render structured insights as markdown."""
        if not self.insights:
            return ""

        sections = []
        for section in self.insights:
            heading = section.get("heading", "")
            points = section.get("points", [])

            if heading:
                lines = [f"### {heading}"]
                for point in points:
                    lines.append(f"- {point}")
                sections.append("\n".join(lines))

        return "\n\n".join(sections)


class Country(models.Model):
    """Political/regulatory entity with country-specific insights.

    Examples: United States, Canada, Sweden, Switzerland

    Country insights capture regulatory requirements and local cultural
    nuances specific to that country.
    """

    code = models.CharField(
        max_length=2,
        unique=True,
        help_text="ISO 3166-1 alpha-2 code (e.g., 'US', 'CA', 'SE')",
    )
    name = models.CharField(
        max_length=100,
        help_text="Official country name",
    )
    default_language = models.ForeignKey(
        "Language",
        on_delete=models.PROTECT,
        related_name="default_for_countries",
        null=True,
        blank=True,
        help_text="Primary/default language for this country",
    )
    insights = models.JSONField(
        default=list,
        help_text="Country-specific regulatory and cultural rules: [{heading, points[]}]",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # M2M relationships
    regions = models.ManyToManyField(
        Region,
        through="CountryRegion",
        related_name="countries",
        blank=True,
        help_text="Regions this country belongs to",
    )
    languages = models.ManyToManyField(
        "Language",
        through="CountryLanguage",
        related_name="countries",
        blank=True,
        help_text="All languages spoken in this country",
    )

    class Meta:
        db_table = "core_country"
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def insights_as_markdown(self) -> str:
        """Render structured insights as markdown."""
        if not self.insights:
            return ""

        sections = []
        for section in self.insights:
            heading = section.get("heading", "")
            points = section.get("points", [])

            if heading:
                lines = [f"### {heading}"]
                for point in points:
                    lines.append(f"- {point}")
                sections.append("\n".join(lines))

        return "\n\n".join(sections)

    def get_primary_languages(self):
        """Get languages marked as primary for this country."""
        return self.languages.filter(countrylanguage__is_primary=True)


class Language(models.Model):
    """Language variant with locale code and LLM model recommendations.

    Examples: en-US, fr-CA, de-CH, es-MX

    Each language has locale-specific insights and recommended LLM models
    for generating content in that language variant.
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO 639 + country locale (e.g., 'en-US', 'fr-CA')",
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'English (United States)')",
    )
    base_language = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ISO 639-1 base language code (e.g., 'en', 'fr', 'de')",
    )
    primary_model = models.ForeignKey(
        LLMModel,
        on_delete=models.PROTECT,
        related_name="primary_for_languages",
        help_text="Recommended LLM model for this language",
    )
    alternative_models = models.ManyToManyField(
        LLMModel,
        through="LanguageAlternativeModel",
        related_name="alternative_for_languages",
        blank=True,
        help_text="Alternative LLM models that can handle this language",
    )
    insights = models.JSONField(
        default=list,
        help_text="Language-specific localization guidance: [{heading, points[]}]",
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
        indexes = [
            models.Index(fields=["base_language", "is_active"], name="lang_base_active_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def insights_as_markdown(self) -> str:
        """Render structured insights as markdown."""
        if not self.insights:
            return ""

        sections = []
        for section in self.insights:
            heading = section.get("heading", "")
            points = section.get("points", [])

            if heading:
                lines = [f"### {heading}"]
                for point in points:
                    lines.append(f"- {point}")
                sections.append("\n".join(lines))

        return "\n\n".join(sections)

    def get_all_models(self):
        """Get primary model plus all alternatives as a queryset."""
        from django.db.models import Q

        return LLMModel.objects.filter(
            Q(pk=self.primary_model_id) | Q(alternative_for_languages=self)
        ).distinct()


# M2M Through Tables


class CountryRegion(models.Model):
    """Many-to-many through table for Country ↔ Region relationship.

    Allows countries to belong to multiple regions (e.g., Switzerland in
    both DACH and EU-WEST).
    """

    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    class Meta:
        db_table = "core_country_region"
        unique_together = [["country", "region"]]
        verbose_name = "Country-Region Mapping"
        verbose_name_plural = "Country-Region Mappings"

    def __str__(self):
        return f"{self.country.code} → {self.region.code}"


class CountryLanguage(models.Model):
    """Many-to-many through table for Country ↔ Language relationship.

    Tracks which languages are spoken in each country, with is_primary flag
    to indicate the default/official language.
    """

    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary/official language for this country",
    )

    class Meta:
        db_table = "core_country_language"
        unique_together = [["country", "language"]]
        verbose_name = "Country-Language Mapping"
        verbose_name_plural = "Country-Language Mappings"

    def __str__(self):
        primary_marker = " (primary)" if self.is_primary else ""
        return f"{self.country.code} → {self.language.code}{primary_marker}"


class LanguageAlternativeModel(models.Model):
    """Many-to-many through table for Language ↔ LLMModel alternatives.

    Tracks alternative LLM models that can handle a specific language,
    separate from the primary model recommendation.
    """

    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    llmmodel = models.ForeignKey(LLMModel, on_delete=models.CASCADE)

    class Meta:
        db_table = "core_language_alternative_model"
        unique_together = [["language", "llmmodel"]]
        verbose_name = "Language Alternative Model"
        verbose_name_plural = "Language Alternative Models"

    def __str__(self):
        return f"{self.language.code} → {self.llmmodel.name}"
