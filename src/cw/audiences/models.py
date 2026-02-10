"""
Audience segmentation models.

This module provides database models for:
- Geographic segmentation: Regions, Countries, Languages
- Compositional insights at each level (Region → Country → Language)

Models relocated from core app to establish dedicated audiences namespace.
"""

from django.db import models


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
        "core.LLMModel",
        on_delete=models.PROTECT,
        related_name="primary_for_languages",
        help_text="Recommended LLM model for this language",
    )
    alternative_models = models.ManyToManyField(
        "core.LLMModel",
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

        from cw.core.models import LLMModel

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
    llmmodel = models.ForeignKey("core.LLMModel", on_delete=models.CASCADE)

    class Meta:
        db_table = "core_language_alternative_model"
        unique_together = [["language", "llmmodel"]]
        verbose_name = "Language Alternative Model"
        verbose_name_plural = "Language Alternative Models"

    def __str__(self):
        return f"{self.language.code} → {self.llmmodel.name}"


# Non-Geographic Segmentation Models


class Segment(models.Model):
    """Non-geographic audience segment (demographic, behavioral, psychographic).

    Examples:
    - Demographic: Household Income → Middle-Income
    - Behavioral: Usage Pattern → First-Time Users
    - Psychographic: Emotional Driver → Nostalgia

    Geographic segmentation uses existing Region/Country/Language models.
    """

    CATEGORY_CHOICES = [
        ("DEMOGRAPHIC", "Demographic"),
        ("BEHAVIORAL", "Behavioral"),
        ("PSYCHOGRAPHIC", "Psychographic"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Segment category",
    )
    vector = models.CharField(
        max_length=100,
        help_text="Dimension being segmented (e.g., 'Household Income', 'Emotional Driver')",
    )
    value = models.CharField(
        max_length=100,
        help_text="Position on the dimension (e.g., 'Middle-Income', 'Escapism')",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer description",
    )
    insights = models.JSONField(
        default=list,
        help_text="Structured insights: [{heading, points[]}]",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "audiences_segment"
        ordering = ["category", "vector", "value"]
        verbose_name = "Segment"
        verbose_name_plural = "Segments"
        unique_together = [["category", "vector", "value"]]

    def __str__(self):
        return f"{self.get_category_display()}: {self.vector} → {self.value}"

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


class Persona(models.Model):
    """Named collection of segments representing a target audience profile.

    A Persona combines geographic segments (Region/Country/Language) with
    non-geographic segments (Demographic/Behavioral/Psychographic) to create
    a complete audience profile.

    Example: "Budget-Conscious First-Timer"
    - Geographic: North America / United States / English (en-US)
    - Demographic: Household Income → Middle-Income
    - Behavioral: Usage Pattern → First-Time Users
    - Psychographic: Emotional Driver → Nostalgia
    """

    name = models.CharField(
        max_length=200,
        help_text="Persona name (e.g., 'Budget-Conscious First-Timer')",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of this persona",
    )

    # Geographic segments (reuse existing models)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personas",
        help_text="Target region",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personas",
        help_text="Target country",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personas",
        help_text="Target language",
    )

    # Non-geographic segments
    segments = models.ManyToManyField(
        Segment,
        through="PersonaSegment",
        related_name="personas",
        blank=True,
        help_text="Demographic, behavioral, and psychographic segments",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "audiences_persona"
        ordering = ["name"]
        verbose_name = "Persona"
        verbose_name_plural = "Personas"

    def __str__(self):
        parts = [self.name]
        if self.region or self.country or self.language:
            geo = []
            if self.region:
                geo.append(self.region.code)
            if self.country:
                geo.append(self.country.code)
            if self.language:
                geo.append(self.language.code)
            parts.append(f"({'/'.join(geo)})")
        return " ".join(parts)

    def segment_count(self) -> int:
        """Count of attached non-geographic segments."""
        return self.segments.count()


class PersonaSegment(models.Model):
    """Many-to-many through table for Persona ↔ Segment relationship.

    Explicit through table for future extensibility.
    Segments are automatically sorted by category and vector.
    """

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    segment = models.ForeignKey(Segment, on_delete=models.CASCADE)

    class Meta:
        db_table = "audiences_persona_segment"
        unique_together = [["persona", "segment"]]
        ordering = ["segment__category", "segment__vector", "segment__value"]
        verbose_name = "Persona Segment"
        verbose_name_plural = "Persona Segments"

    def __str__(self):
        return f"{self.persona.name} → {self.segment}"
