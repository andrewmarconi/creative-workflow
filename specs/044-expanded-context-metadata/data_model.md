# Data Model: Expanded Context Metadata

**Issue:** #44
**Last Updated:** 2026-02-06

---

## Model Architecture Overview

The refactored system uses a **dimensional reference data model** with **compositional insights**:

- **4 Core Reference Tables**: Region, Country, Language, Culture
- **M2M Relationships**: Flexible many-to-many associations
- **Flat Adaptation Hierarchy**: Single parent reference, no deep nesting
- **Insights Cascade**: Region → Country → Language → Market

---

## Entity-Relationship Diagram

```{mermaid}
erDiagram
    %% ============================================
    %% CORE REFERENCE DATA (src/cw/core/models.py)
    %% ============================================

    Region {
        int id PK
        string code UK "e.g., 'NA', 'NORDICS', 'DACH'"
        string name "e.g., 'North America'"
        text description
        json insights "Regional cultural patterns"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    Country {
        int id PK
        string code UK "ISO 3166-1 alpha-2 (e.g., 'US', 'CA')"
        string name "e.g., 'United States'"
        int default_language_id FK
        json insights "Country-specific regulatory and cultural rules"
        text notes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    Culture {
        int id PK
        string code UK "e.g., 'nordic-minimalism'"
        string name "e.g., 'Nordic Minimalism'"
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    Language {
        int id PK
        string code UK "ISO 639 + country (e.g., 'en-US', 'fr-CA')"
        string name "e.g., 'English (United States)'"
        string base_language "ISO 639-1 (e.g., 'en', 'fr')"
        int primary_model_id FK
        json insights "Language-specific localization guidance"
        text notes
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    LLMModel {
        int id PK
        string model_id UK "HuggingFace ID"
        string name "Display name"
        text notes
        boolean is_active
        boolean load_in_4bit
        datetime created_at
        datetime updated_at
    }

    %% ============================================
    %% M2M THROUGH TABLES
    %% ============================================

    CountryRegion {
        int id PK
        int country_id FK
        int region_id FK
    }

    CountryLanguage {
        int id PK
        int country_id FK
        int language_id FK
        boolean is_primary "Primary language for this country"
    }

    RegionCulture {
        int id PK
        int region_id FK
        int culture_id FK
    }

    LanguageAlternativeModel {
        int id PK
        int language_id FK
        int llmmodel_id FK
    }

    %% ============================================
    %% TV SPOTS APP (src/cw/tvspots/models.py)
    %% ============================================

    AdaptationMarket {
        int id PK
        string name UK "e.g., 'US Hispanic'"
        string code UK "e.g., 'us-hispanic'"
        int default_language_id FK "Optional override"
        json insights "Market-specific positioning and targeting"
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    AdaptationMarketRegion {
        int id PK
        int adaptationmarket_id FK
        int region_id FK
    }

    AdaptationMarketCountry {
        int id PK
        int adaptationmarket_id FK
        int country_id FK
    }

    AdaptationMarketCulture {
        int id PK
        int adaptationmarket_id FK
        int culture_id FK
    }

    TvSpot {
        int id PK
        string client_name
        string brand_name
        string script_title
        int total_runtime_seconds
        string job_id UK
        text notes
        datetime created_at
        datetime updated_at
    }

    TvSpotVersion {
        int id PK
        int tv_spot_id FK
        string version_type "origin | adaptation"
        int market_id FK "NULL for origin"
        string code "e.g., 'ORIGIN', 'US-HISP'"
        string name "e.g., 'US Hispanic Adaptation'"
        int language_id FK "CHANGED: FK instead of CharField"
        text visual_style_prompt
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    TVSpotAdaptation {
        int id PK
        string job_id UK "Internal tracking ID"
        string title
        int source_adaptation_id FK "Self-referential parent"
        int region_id FK "Optional - use what applies"
        int country_id FK "Optional"
        int language_id FK "Optional"
        text adaptation_notes
        json script_data "Full script content"
        datetime created_at
        datetime updated_at
    }

    TVSpotAdaptationCulture {
        int id PK
        int tvspotadaptation_id FK
        int culture_id FK
    }

    AdaptationJob {
        int id PK
        int tv_spot_id FK
        int origin_version_id FK
        int target_market_id FK
        int language_id FK "Optional override"
        int llm_model_id FK "Optional override"
        int result_version_id FK "One-to-one"
        string status
        string celery_task_id
        text error_message
        boolean use_pipeline
        json concept_brief
        json cultural_brief
        json evaluation_history
        json pipeline_metadata
        datetime created_at
        datetime started_at
        datetime completed_at
    }

    TvSpotScriptRow {
        int id PK
        int tv_spot_version_id FK
        int order_index
        string shot_number
        string timecode_start
        decimal duration_seconds
        text visual_text
        text audio_text
    }

    %% ============================================
    %% CORE RELATIONSHIPS
    %% ============================================

    Country ||--o{ CountryRegion : "belongs to"
    Region ||--o{ CountryRegion : "contains"

    Country ||--o{ CountryLanguage : "has languages"
    Language ||--o{ CountryLanguage : "spoken in"

    Region ||--o{ RegionCulture : "associated with"
    Culture ||--o{ RegionCulture : "manifests in"

    Language ||--o| LLMModel : "primary_model"
    Language ||--o{ LanguageAlternativeModel : "alternatives"
    LLMModel ||--o{ LanguageAlternativeModel : "alternative for"

    Country ||--o| Language : "default_language"

    %% ============================================
    %% TVSPOTS RELATIONSHIPS
    %% ============================================

    AdaptationMarket ||--o{ AdaptationMarketRegion : "targets"
    Region ||--o{ AdaptationMarketRegion : "targeted by"

    AdaptationMarket ||--o{ AdaptationMarketCountry : "targets"
    Country ||--o{ AdaptationMarketCountry : "targeted by"

    AdaptationMarket ||--o{ AdaptationMarketCulture : "considers"
    Culture ||--o{ AdaptationMarketCulture : "considered in"

    AdaptationMarket ||--o| Language : "default_language"

    TvSpot ||--o{ TvSpotVersion : "has versions"
    TvSpotVersion }o--|| AdaptationMarket : "for market"
    TvSpotVersion }o--|| Language : "in language"

    TvSpotVersion ||--o{ TvSpotScriptRow : "contains"

    TVSpotAdaptation }o--o| TVSpotAdaptation : "source_adaptation (self-ref)"
    TVSpotAdaptation }o--o| Region : "region (optional)"
    TVSpotAdaptation }o--o| Country : "country (optional)"
    TVSpotAdaptation }o--o| Language : "language (optional)"
    TVSpotAdaptation ||--o{ TVSpotAdaptationCulture : "cultures"
    Culture ||--o{ TVSpotAdaptationCulture : "applied to"

    TvSpot ||--o{ AdaptationJob : "adaptation requests"
    TvSpotVersion ||--o{ AdaptationJob : "origin_version"
    AdaptationMarket ||--o{ AdaptationJob : "target_market"
    Language ||--o{ AdaptationJob : "language override"
    LLMModel ||--o{ AdaptationJob : "model override"
    AdaptationJob ||--o| TvSpotVersion : "result_version"

    %% ============================================
    %% STYLING
    %% ============================================

    classDef coreModel fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    classDef tvspotsModel fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef junctionTable fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px

    class Region,Country,Culture,Language,LLMModel coreModel
    class AdaptationMarket,TvSpot,TvSpotVersion,TVSpotAdaptation,AdaptationJob,TvSpotScriptRow tvspotsModel
    class CountryRegion,CountryLanguage,RegionCulture,LanguageAlternativeModel,AdaptationMarketRegion,AdaptationMarketCountry,AdaptationMarketCulture,TVSpotAdaptationCulture junctionTable
```

---

## Model Definitions

### Core Models (src/cw/core/models.py)

#### Region

```python
class Region(models.Model):
    """Cultural/market grouping with regional insights.

    Examples: North America, Nordics, DACH, LATAM
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code (e.g., 'NA', 'NORDICS', 'DACH')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'North America')"
    )
    description = models.TextField(
        blank=True,
        help_text="Region description and scope"
    )
    insights = models.JSONField(
        default=list,
        help_text="Regional cultural patterns: [{heading, points[]}]",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # M2M relationships
    countries = models.ManyToManyField(
        'Country',
        through='CountryRegion',
        related_name='regions',
        blank=True
    )
    cultures = models.ManyToManyField(
        'Culture',
        through='RegionCulture',
        related_name='regions',
        blank=True
    )

    class Meta:
        db_table = 'core_region'
        ordering = ['name']
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'

    def __str__(self):
        return self.name

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
```

#### Country

```python
class Country(models.Model):
    """Political/regulatory entity with country-specific insights.

    Examples: United States, Canada, Sweden, Switzerland
    """

    code = models.CharField(
        max_length=2,
        unique=True,
        help_text="ISO 3166-1 alpha-2 code (e.g., 'US', 'CA', 'SE')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Official country name"
    )
    default_language = models.ForeignKey(
        'Language',
        on_delete=models.PROTECT,
        related_name='default_for_countries',
        null=True,
        blank=True,
        help_text="Primary/default language for this country"
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
    languages = models.ManyToManyField(
        'Language',
        through='CountryLanguage',
        related_name='countries',
        blank=True,
        help_text="All languages spoken in this country"
    )

    class Meta:
        db_table = 'core_country'
        ordering = ['name']
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.name

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
        return self.languages.filter(
            countrylanguage__is_primary=True
        )
```

#### Language

```python
class Language(models.Model):
    """Language variant with locale code and LLM model recommendations.

    Examples: en-US, fr-CA, de-CH, es-MX
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO 639 + country locale (e.g., 'en-US', 'fr-CA')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'English (United States)')"
    )
    base_language = models.CharField(
        max_length=10,
        help_text="ISO 639-1 base language code (e.g., 'en', 'fr', 'de')"
    )
    primary_model = models.ForeignKey(
        'LLMModel',
        on_delete=models.PROTECT,
        related_name='primary_for_languages',
        help_text="Recommended LLM model for this language"
    )
    alternative_models = models.ManyToManyField(
        'LLMModel',
        through='LanguageAlternativeModel',
        related_name='alternative_for_languages',
        blank=True,
        help_text="Alternative LLM models that can handle this language"
    )
    insights = models.JSONField(
        default=list,
        help_text="Language-specific localization guidance: [{heading, points[]}]",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_language'
        ordering = ['name']
        verbose_name = 'Language'
        verbose_name_plural = 'Languages'

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
```

#### Culture

```python
class Culture(models.Model):
    """Cultural theme/characteristic that can span multiple regions.

    Examples: Nordic Minimalism, Germanic Formality, Latin Warmth
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Slug identifier (e.g., 'nordic-minimalism')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Nordic Minimalism')"
    )
    description = models.TextField(
        help_text="Description of cultural characteristics"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_culture'
        ordering = ['name']
        verbose_name = 'Culture'
        verbose_name_plural = 'Cultures'

    def __str__(self):
        return self.name
```

---

## Key Design Decisions

### 1. Insights at Multiple Levels

**Decision:** Store insights at Region, Country, Language, and Market levels

**Rationale:**
- Eliminates duplication of broad regional insights across markets
- Language-specific rules apply regardless of market
- Country regulations relevant to all adaptations for that country

### 2. Flat Adaptation Hierarchy

**Decision:** `TVSpotAdaptation.source_adaptation` (single parent) instead of deep tree

**Rationale:**
- Simpler queries and traversal
- Agency workflows rarely need >2 levels
- Can still model: Master → Regional → Country chains

### 3. Optional Dimensional Tagging

**Decision:** All dimensional FKs (`region`, `country`, `language`, `culture`) are nullable

**Rationale:**
- Flexibility: Tag with what applies (language-only, country+language, etc.)
- No forced categorization
- Supports edge cases (test markets, experimental campaigns)

### 4. Language FK with Soft Validation

**Decision:** `TvSpotVersion.language` is FK (not CharField), but no hard country restriction

**Rationale:**
- Proper relational integrity
- LLM model associations
- Allow unusual combinations with warnings (e.g., Chinese for US market)

---

## Migration Considerations

### Breaking Changes

1. **TvSpotVersion.language**: `CharField` → `ForeignKey(Language)`
   - Requires data migration to look up Language by code
   - Existing codes like `"en-US"` must match new locale-based Language entries

2. **New Required Models**: Region, Country, Culture must be seeded before migrations

### Migration Strategy

See [migration_strategy.md](./migration_strategy.md) for detailed migration plan.

---

## Query Examples

### Get All Adaptations for a Region

```python
# All adaptations tagged with "Nordics" region
nordic_adaptations = TVSpotAdaptation.objects.filter(region__code='NORDICS')
```

### Get All French-Language Versions

```python
# All versions in any French variant
french_versions = TvSpotVersion.objects.filter(
    language__base_language='fr'
).select_related('language', 'market')
```

### Get Recommended Languages for Country

```python
# Languages suggested for Canada
canada = Country.objects.get(code='CA')
recommended = canada.languages.filter(
    countrylanguage__is_primary=True
)
# Returns: en-CA (primary)

all_languages = canada.languages.all()
# Returns: en-CA, fr-CA
```

### Compose Insights for Adaptation

```python
def get_composite_insights(adaptation_job):
    """Aggregate insights from all applicable levels."""
    insights_collection = []

    # Region insights
    if adaptation_job.region:
        insights_collection.append({
            'source': f'Region: {adaptation_job.region.name}',
            'content': adaptation_job.region.insights_as_markdown()
        })

    # Country insights
    if adaptation_job.country:
        insights_collection.append({
            'source': f'Country: {adaptation_job.country.name}',
            'content': adaptation_job.country.insights_as_markdown()
        })

    # Language insights
    language = adaptation_job.effective_language
    insights_collection.append({
        'source': f'Language: {language.name}',
        'content': language.insights_as_markdown()
    })

    # Market insights
    insights_collection.append({
        'source': f'Market: {adaptation_job.target_market.name}',
        'content': adaptation_job.target_market.rules_as_markdown()
    })

    return insights_collection
```

---

## Index Strategy

Recommended indexes for query performance:

```python
# In migrations
class Migration(migrations.Migration):
    operations = [
        # ...
        migrations.AddIndex(
            model_name='language',
            index=models.Index(fields=['base_language', 'is_active'], name='lang_base_active_idx'),
        ),
        migrations.AddIndex(
            model_name='tvspotversion',
            index=models.Index(fields=['language', 'market'], name='version_lang_market_idx'),
        ),
        migrations.AddIndex(
            model_name='tvspotadaptation',
            index=models.Index(fields=['region', 'country', 'language'], name='adapt_dims_idx'),
        ),
    ]
```

---

## References

- [PRD](./prd.md)
- [Default Data](./default_data.md)
- [Implementation Plan](./implementation_plan.md)
