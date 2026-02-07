# Insights Composition: Multi-Level Guidance for Adaptations

**Issue:** #44
**Last Updated:** 2026-02-06

---

## Overview

The expanded context metadata system stores **insights** (cultural, linguistic, and regulatory guidance) at four levels:

1. **Region** - Broad cultural patterns
2. **Country** - Regulatory and local cultural nuances
3. **Language** - Linguistic rules and localization guidelines
4. **Market** - Campaign-specific positioning and targeting

When generating an adaptation, these insights **compose hierarchically** to provide comprehensive, non-duplicated guidance to the LLM.

---

## Insights Structure

All insights use the same JSON schema across models:

```text
{
  "insights": [
    {
      "heading": "Section Title",
      "points": [
        "Bullet point 1",
        "Bullet point 2",
        "..."
      ]
    },
    {
      "heading": "Another Section",
      "points": [...]
    }
  ]
}
```

**Markdown Rendering:**

```markdown
### Section Title
- Bullet point 1
- Bullet point 2

### Another Section
- ...
```

---

## Composition Logic

### Hierarchy: Broad → Specific

```
Region (Cultural Patterns)
  ↓
Country (Regulatory + Local Culture)
  ↓
Language (Linguistic Rules)
  ↓
Market (Campaign Positioning)
```

**Principle:** More specific levels override or extend broader levels.

### Example: Quebec French Adaptation

**Input:**
- Region: North America (or not specified)
- Country: Canada
- Language: fr-CA (Quebec French)
- Market: "Quebec Premium Consumers"

**Composed Insights:**

```markdown
# Adaptation Guidance for Quebec Premium Consumers

## Regional Insights: North America
### Cultural values
- Direct, benefit-oriented messaging resonates
- Casual tone and informal address acceptable in most contexts
- Aspirational optimism and personal achievement themes

## Country Insights: Canada
### Regulatory requirements
- Quebec: Bill 96 mandates French text at least 2x size of English in advertising
- CRTC regulates broadcast advertising
- CASL requires explicit opt-in for commercial electronic messages

### Cultural considerations
- Distinct French-Canadian (Québécois) vs European French cultural identity
- Avoid conflating Canadian with American culture - unique national identity

### Language segmentation
- French Canada (Quebec): 21% - requires separate creative
- Bilingual markets (Montreal, Ottawa) need dual-language versions

## Language Insights: French (Quebec)
### Vocabulary differences from France
- Car: 'char' (QC) vs 'voiture' (FR)
- Breakfast: 'déjeuner' (QC) vs 'petit-déjeuner' (FR)
- Weekend: 'fin de semaine' (QC) vs 'weekend' (FR)

### Pronunciation and idioms
- Quebec French has distinct phonology - MUST use Quebec VO talent, not European
- Local idioms: 'C'est le fun' (it's fun), 'Tiguidou' (great/okay)
- Informal 'tu' more common than formal 'vous' in advertising

### Legal and compliance
- Office québécois de la langue française enforces French language use
- Bill 101 (Charter of the French Language) sets commercial French requirements
- All product descriptions, warnings, and supers MUST be in French

## Market Insights: Quebec Premium Consumers
### Positioning strategy
- Emphasize quality and craftsmanship over price
- Local Quebec brands and heritage resonate
- Environmental sustainability important to this segment

### Tone
- Sophisticated but warm - not overly formal
- Cultural pride acceptable (Quebec identity)
- Avoid European French elitism
```

---

## Implementation

### Composition Helper Function

**Location:** `src/cw/lib/insights.py`

```python
"""Insights composition for multi-level adaptation guidance."""

from typing import List, Dict, Optional


def compose_insights(adaptation_job) -> List[Dict[str, str]]:
    """Aggregate insights from region → country → language → market.

    Args:
        adaptation_job: AdaptationJob instance with dimensional references

    Returns:
        List of insight sections with source attribution:
        [
            {
                'source': 'Region: North America',
                'markdown': '### Cultural values\\n- ...'
            },
            ...
        ]
    """
    insights = []

    # 1. Region-level insights (if applicable)
    region = _get_region(adaptation_job)
    if region and region.insights:
        insights.append({
            'source': f'Region: {region.name}',
            'markdown': region.insights_as_markdown()
        })

    # 2. Country-level insights (if applicable)
    country = _get_country(adaptation_job)
    if country and country.insights:
        insights.append({
            'source': f'Country: {country.name}',
            'markdown': country.insights_as_markdown()
        })

    # 3. Language-level insights (always present)
    language = adaptation_job.effective_language
    if language and language.insights:
        insights.append({
            'source': f'Language: {language.name}',
            'markdown': language.insights_as_markdown()
        })

    # 4. Market-level insights (campaign-specific)
    market = adaptation_job.target_market
    if market and market.rules:  # Note: 'rules' is legacy name, may rename to 'insights'
        insights.append({
            'source': f'Market: {market.name}',
            'markdown': market.rules_as_markdown()
        })

    return insights


def compose_insights_as_markdown(adaptation_job) -> str:
    """Compose all insights into a single Markdown document.

    Args:
        adaptation_job: AdaptationJob instance

    Returns:
        Markdown string with all insights hierarchically organized
    """
    sections = compose_insights(adaptation_job)

    if not sections:
        return ""

    # Build full document
    lines = [
        f"# Adaptation Guidance for {adaptation_job.target_market.name}",
        ""
    ]

    for section in sections:
        lines.append(f"## {section['source']}")
        lines.append(section['markdown'])
        lines.append("")  # Blank line between sections

    return "\n".join(lines)


def _get_region(adaptation_job) -> Optional['Region']:
    """Extract region from adaptation job (via market or direct reference).

    Priority:
    1. Direct region reference (if TVSpotAdaptation model)
    2. Market's regions (if AdaptationMarket has M2M to regions)
    3. Country's regions (via market's countries)
    """
    # Direct reference (TVSpotAdaptation model)
    if hasattr(adaptation_job, 'region') and adaptation_job.region:
        return adaptation_job.region

    # Via market regions (M2M)
    market = adaptation_job.target_market
    if hasattr(market, 'regions'):
        return market.regions.first()  # Pick first if multiple

    # Via country
    country = _get_country(adaptation_job)
    if country and hasattr(country, 'regions'):
        return country.regions.first()

    return None


def _get_country(adaptation_job) -> Optional['Country']:
    """Extract country from adaptation job.

    Priority:
    1. Direct country reference (if TVSpotAdaptation model)
    2. Market's countries (if AdaptationMarket has M2M)
    3. Language's countries (via effective_language)
    """
    # Direct reference
    if hasattr(adaptation_job, 'country') and adaptation_job.country:
        return adaptation_job.country

    # Via market countries (M2M)
    market = adaptation_job.target_market
    if hasattr(market, 'countries'):
        return market.countries.first()

    # Via language
    language = adaptation_job.effective_language
    if language and hasattr(language, 'countries'):
        return language.countries.filter(
            countrylanguage__is_primary=True
        ).first()

    return None
```

---

## Integration with Adaptation Pipeline

### Single-Step Adaptation

**Location:** `src/cw/lib/adaptation.py`

```python
from cw.lib.insights import compose_insights_as_markdown

class AdaptationGenerator:
    def _build_prompt(self, original_spot, target_market, language, creativity):
        """Build adaptation prompt with composed insights."""

        # Compose insights from all levels
        insights_markdown = compose_insights_as_markdown(adaptation_job)

        user_prompt = render_prompt(
            "adaptation.j2",
            target_market_name=target_market.name,
            target_market_language=language.code,
            target_market_insights=insights_markdown,  # Composite insights
            original_json=original_json,
            # ...
        )

        # ... rest of prompt building
```

**Template Update:** `templates/prompts/adaptation.j2`

```django
You are adapting a TV spot for {{ target_market_name }}.

## Adaptation Guidelines

{{ target_market_insights }}

## Original TV Spot

```text
{{ original_json }}
```

## Task

Create a culturally-adapted version following the guidelines above.
Maintain the same structure and timing while adapting:
- Cultural references and idioms
- Visual elements that may not resonate
- Tone and register for the target market
- Language to {{ target_market_language }}

Output the adapted script as JSON matching the AdaptationOutput schema.
```

---

### Multi-Agent Pipeline

**Location:** `src/cw/lib/pipeline/nodes.py`

Each pipeline node receives composed insights:

```python
from cw.lib.insights import compose_insights

def concept_extraction_node(state: PipelineState) -> PipelineState:
    """Extract core concepts - uses insights for context."""

    # Fetch adaptation job
    job = AdaptationJob.objects.get(pk=state['job_id'])

    # Compose insights
    insights = compose_insights(job)

    # Build prompt with insights
    prompt = render_prompt(
        'pipeline/concept_extraction.j2',
        original_script=state['original_script'],
        target_market=state['target_market_name'],
        insights=insights,  # Pass to template
    )

    # Generate concept brief...
    # ...
```

**Template:** `templates/prompts/pipeline/concept_extraction.j2`

```django
# Task: Concept Extraction

Analyze this TV spot and extract core concepts, themes, and creative intent.

## Market Context

{% for insight_section in insights %}
### {{ insight_section.source }}
{{ insight_section.markdown }}
{% endfor %}

## Original Script

{{ original_script }}

## Instructions

Extract:
1. Core message and selling proposition
2. Emotional beats and narrative structure
3. Universal themes vs culture-specific elements
4. What must be preserved vs what can be adapted

Consider the market insights above when identifying cultural assumptions.

Output as JSON matching ConceptBrief schema.
```

---

## Insights Deduplication Strategy

### Problem: Overlapping Insights

**Scenario:** Both Region and Country mention "Environmental sustainability important"

**Solution 1: Manual Curation** (Recommended)
- When creating reference data, ensure insights are at appropriate level
- Region: Broad patterns ("Sustainability valued across Nordics")
- Country: Specific regulations ("Sweden requires environmental claim substantiation")

**Solution 2: Automatic Deduplication** (Future Enhancement)
```python
def deduplicate_insights(insights: List[Dict]) -> List[Dict]:
    """Remove duplicate insight points across levels."""
    seen_points = set()
    deduped = []

    for section in insights:
        # Parse markdown to extract bullet points
        points = _extract_bullet_points(section['markdown'])

        # Filter duplicates
        unique_points = [p for p in points if p not in seen_points]
        seen_points.update(unique_points)

        if unique_points:
            # Rebuild markdown with unique points only
            section['markdown'] = _rebuild_markdown(unique_points)
            deduped.append(section)

    return deduped
```

---

## Benefits of Multi-Level Insights

### 1. No Duplication

**Before (single Market model):**
```
Market: "US Hispanic"
- Family-oriented messaging (✓)
- Aspirational optimism (✓)
- Direct tone (✓)

Market: "US Asian"
- Family-oriented messaging (duplicate!)
- Aspirational optimism (duplicate!)
- Direct tone (duplicate!)
```

**After (multi-level):**
```
Region: "North America"
- Aspirational optimism
- Direct tone

Market: "US Hispanic"
- Family-oriented messaging (specific to this market)

Market: "US Asian"
- Respect for hierarchy (specific to this market)
```

### 2. Reusability

**Language insights apply everywhere:**
- fr-CA vocabulary rules apply to all Quebec markets (premium, youth, mainstream)
- de-DE formality rules apply to all German markets

**Country insights apply to all languages:**
- Canada Bill 96 applies whether adapting to en-CA or fr-CA

### 3. Maintainability

**Update once, apply everywhere:**
- Change Nordic cultural insights → affects SE, NO, DK, FI automatically
- Update Spanish (Spain) vocabulary → affects all es-ES markets

### 4. Flexibility

**Tag what applies:**
- Language-only adaptation: Just language insights
- Regional adaptation: Region + country + language insights
- Niche market: All four levels for maximum specificity

---

## Query Examples

### Get All Insights for an Adaptation

```python
from cw.lib.insights import compose_insights_as_markdown

job = AdaptationJob.objects.get(pk=123)
insights_md = compose_insights_as_markdown(job)
print(insights_md)
```

### Get Insights for a Market Preview (Before Creating Job)

```python
from cw.tvspots.models import AdaptationMarket
from cw.core.models import Language

market = AdaptationMarket.objects.get(code='us-hispanic')
language = Language.objects.get(code='es-US')

# Simulate job for preview
class PreviewJob:
    target_market = market
    effective_language = language

insights = compose_insights(PreviewJob())
```

### Update Insights for a Region

```python
from cw.core.models import Region

nordics = Region.objects.get(code='NORDICS')

# Add new insight section
nordics.insights.append({
    "heading": "Media preferences",
    "points": [
        "High trust in public broadcasting",
        "Ad-free public TV common (except commercial breaks)",
        "Digital and streaming platforms widely adopted"
    ]
})
nordics.save()

# Now all Nordic adaptations get these insights
```

---

## Testing Strategy

### Unit Tests

```python
def test_compose_insights_all_levels():
    """Test insights from all four levels compose correctly."""
    # Setup: Create region, country, language, market with insights
    # ...

    job = AdaptationJob.objects.create(...)
    insights = compose_insights(job)

    assert len(insights) == 4
    assert insights[0]['source'].startswith('Region:')
    assert insights[1]['source'].startswith('Country:')
    assert insights[2]['source'].startswith('Language:')
    assert insights[3]['source'].startswith('Market:')


def test_compose_insights_partial():
    """Test insights compose with missing levels (e.g., no region)."""
    # Setup: Only country, language, market (no region)
    # ...

    job = AdaptationJob.objects.create(...)
    insights = compose_insights(job)

    assert len(insights) == 3  # No region section
    assert all('Region:' not in i['source'] for i in insights)
```

### Integration Tests

```python
def test_adaptation_with_composed_insights():
    """Test full adaptation flow uses composed insights."""
    from cw.lib.adaptation import AdaptationGenerator

    generator = AdaptationGenerator()
    job = AdaptationJob.objects.create(...)

    # Generate adaptation
    result = generator.adapt(job)

    # Verify insights were used (check logs or prompt)
    # ...
```

---

## Future Enhancements

### 1. Insight Versioning

Track when insights change:

```python
class Region(models.Model):
    # ...
    insights_version = models.IntegerField(default=1)
    insights_updated_at = models.DateTimeField(auto_now=True)
```

### 2. Insight Analytics

Track which insights correlate with successful adaptations:

```python
class InsightUsage(models.Model):
    adaptation_job = models.ForeignKey(AdaptationJob)
    insight_source = models.CharField(max_length=100)  # "Region: Nordics"
    insight_heading = models.CharField(max_length=200)  # "Cultural values"
    quality_score = models.FloatField()  # From pipeline evaluation
```

### 3. AI-Assisted Insight Generation

Use LLM to suggest insights based on market research:

```python
def suggest_insights(market_name: str, research_text: str) -> List[Dict]:
    """Generate insight suggestions from market research documents."""
    # Use LLM to extract and structure insights
    # ...
```

---

## References

- [PRD](./prd.md)
- [Data Model](./data_model.md)
- [Default Data](./default_data.md)
- [Implementation Plan](./implementation_plan.md)
