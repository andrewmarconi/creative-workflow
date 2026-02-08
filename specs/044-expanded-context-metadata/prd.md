# PRD: Expanded Context Metadata for TV Spot Adaptations

**Issue:** #44
**Status:** Design Phase
**Owner:** Engineering Team
**Created:** 2026-02-06

---

## Executive Summary

Refactor the TV spot adaptation system to handle multi-dimensional regional adaptations, country-specific versions, and language localizations through a flexible, flat reference data model. This replaces the current simple market-based approach with a compositional system that supports complex real-world adaptation patterns.

---

## Problem Statement

Current ad agency workflows involve adaptation patterns that don't map cleanly to a simple hierarchy:

### Current Limitations

1. **Rigid Language Model**
   - `TvSpotVersion.language` is a `CharField` storing locale codes (`"en-US"`, `"fr-CA"`)
   - No relationship to LLM model recommendations
   - No language variant grouping (e.g., all French variants)

2. **Market-Only Context**
   - All cultural/linguistic insights stored only in `AdaptationMarket`
   - Cannot reuse regional insights across multiple markets
   - No country-level regulatory guidance
   - No language-level localization rules

3. **Cannot Model Real Workflows**
   - **Regional → Multi-Language**: Nordics adaptation → Swedish/Norwegian/Danish translations
   - **Multi-Language Countries**: Canada (English/French), Switzerland (German/French/Italian)
   - **Cultural vs Linguistic**: Visual changes vs VO/subtitle swaps

### Pain Points

- **Duplication**: Same cultural insights repeated across related markets
- **Inflexibility**: Cannot easily create "Nordic adaptation" that branches into country-specific versions
- **Poor Reusability**: Language-specific rules (e.g., Quebec French vocabulary) buried in market profiles
- **Weak Modeling**: Flat `language` string doesn't capture locale nuances or model associations

---

## Goals

### Primary Goals

1. **Flexible Dimensional Model**
   - Tag adaptations with `region`, `country`, `language`, `culture` as applicable
   - Support partial tagging (e.g., language-only, or country + language)
   - Flat hierarchy with single parent reference

2. **Compositional Insights**
   - Store insights at appropriate level: Region, Country, Language, Market
   - Aggregate insights when generating adaptations
   - Eliminate duplication while maintaining specificity

3. **Locale-Aware Languages**
   - Change from `"fr"` to `"fr-CA"` (locale-specific codes)
   - Group variants by base language (`"en-US"`, `"en-CA"` → `"en"`)
   - Associate LLM model recommendations per language

4. **Query-Friendly Architecture**
   - M2M relationships for flexible queries
   - Easy to find: "All adaptations for Nordics", "All French-language versions"
   - Support rollups by region, country, or language

### Non-Goals

- ❌ Deep hierarchical nesting (keep flat with single parent)
- ❌ Automated adaptation chaining (manual control preferred)
- ❌ Legacy data migration in this phase (separate migration task)

---

## User Stories

### Story 1: Nordic Regional Adaptation

**As a** creative director
**I want to** create a "Nordic" regional adaptation
**So that** I can then localize it into Swedish, Norwegian, Danish, and Finnish versions

**Acceptance Criteria:**
- ✅ Can create adaptation tagged with `region=Nordics, language=sv-SE`
- ✅ Can create child adaptations: `country=NO, language=no-NO` (parent = Nordic version)
- ✅ Regional insights (minimalism, egalitarianism) flow to all child adaptations

---

### Story 2: Multi-Language Country (Canada)

**As a** marketing manager
**I want to** create separate English and French versions for Canada
**So that** I comply with Quebec language laws and serve both language markets

**Acceptance Criteria:**
- ✅ Can select `country=CA, language=en-CA` or `language=fr-CA`
- ✅ fr-CA version shows Quebec-specific linguistic insights (vocabulary, Bill 96 compliance)
- ✅ Both versions share Canadian country-level insights (regulations, cultural nuances)

---

### Story 3: Language-Specific Localization

**As a** localization specialist
**I want to** access French (Quebec) vocabulary guidelines
**So that** I avoid using European French terms that sound wrong to Quebecois audiences

**Acceptance Criteria:**
- ✅ Language `fr-CA` has insights field with Quebec-specific vocabulary
- ✅ Insights differentiate from `fr-FR` (France) and `fr-BE` (Belgium)
- ✅ Vocabulary rules apply to all markets using `fr-CA`

---

### Story 4: Niche Diaspora Market

**As a** media planner
**I want to** create a Mandarin Chinese adaptation for the US market
**So that** I can target Chinese-American consumers

**Acceptance Criteria:**
- ✅ Can select `country=US, language=zh` (unusual but allowed)
- ✅ System shows warning: "Mandarin not typical for USA. Recommended: en-US, es-US"
- ✅ Can proceed with non-standard language choice
- ✅ Chinese language insights apply (even for US market)

---

## Solution Overview

### Reference Data Models

Four new dimensional tables in `core` app:

1. **Region** - Cultural/market groupings (Nordics, DACH, LATAM)
2. **Country** - Political/regulatory entities (Sweden, Canada, Switzerland)
3. **Language** - Linguistic variants with locale codes (sv-SE, fr-CA, en-US)
4. **Culture** - Cultural themes/characteristics (Nordic minimalism, Germanic formality)

### Flat Adaptation Model

New `TVSpotAdaptation` model with optional dimensional tagging:

```python
class TVSpotAdaptation(models.Model):
    job_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)

    # Flat parent reference (no deep hierarchy)
    source_adaptation = models.ForeignKey('self', null=True, blank=True)

    # Dimensional tags (all optional - use what applies)
    region = models.ForeignKey(Region, null=True, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True)
    language = models.ForeignKey(Language, null=True, blank=True)
    cultures = models.ManyToManyField(Culture, blank=True)

    # Content
    adaptation_notes = models.TextField(blank=True)
    script_data = models.JSONField()
```

### Insights at Every Level

Each level stores appropriate insights:

- **Region**: Broad cultural patterns (minimalism, family values)
- **Country**: Regulatory requirements, local cultural nuances
- **Language**: Linguistic rules, vocabulary, localization guidelines
- **Market**: Campaign-specific positioning and targeting

Insights compose hierarchically when generating adaptations.

---

## Data Model

See [data_model.md](./data_model.md) for complete Mermaid ER diagram and model definitions.

---

## Default Reference Data

See [default_data.md](./default_data.md) for starter regions, countries, languages, and cultures.

---

## Implementation Plan

See [implementation_plan.md](./implementation_plan.md) for phased rollout and migration strategy.

---

## Success Metrics

### Quantitative

- **Reduce Duplication**: 60%+ reduction in repeated cultural insights across markets
- **Query Performance**: Regional rollup queries complete in <100ms
- **Data Consistency**: 0 orphaned language references after migration
- **Adoption**: 80%+ of new adaptations use dimensional tagging within 3 months

### Qualitative

- **User Feedback**: Localization specialists report easier access to language-specific guidance
- **Admin Experience**: Creating Nordic → country adaptations feels intuitive
- **Maintainability**: Adding new languages/countries doesn't require duplicating insights

---

## Open Questions

1. **Culture as Separate Entity vs Region Attributes?**
   - Current design: Separate `Culture` model with M2M to Region
   - Alternative: JSON field on Region with cultural characteristics
   - **Decision needed:** Separate model provides better queryability

2. **Versioning for Adaptations?**
   - Current: No revision history for adaptations
   - Consideration: Add `version` field and `parent_version` FK?
   - **Decision:** Defer to separate feature (not blocking)

3. **Partial Adaptations (Same Video, Different End Card)?**
   - How to model: Same visual, different audio/supers?
   - **Decision:** Use `script_data` JSON flexibility, address in implementation

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Migration data loss | High | Low | Comprehensive data migration with rollback plan |
| Performance degradation (M2M joins) | Medium | Medium | Proper indexing, select_related/prefetch_related |
| User confusion (too many options) | Medium | Medium | Smart defaults, recommended language lists |
| Incomplete reference data | Low | High | Seed common regions/countries/languages on install |

---

## Timeline

- **Week 1**: Model design finalization ✅ (Current)
- **Week 2**: Core models + migrations + seed data
- **Week 3**: Admin UI updates + management commands
- **Week 4**: Library code refactoring (adaptation.py, pipeline)
- **Week 5**: Data migration from CharField to FK
- **Week 6**: Testing + documentation + deployment

---

## References

- [GitHub Issue #44](https://github.com/andrewmarconi/generative-creative-lab/issues/44)
- [Multi-Model Pipeline (Issue #26)](https://github.com/andrewmarconi/generative-creative-lab/tree/main/specs/026_multi_model_pipeline_adaptations/prd.md)
- Current implementation: [src/cw/tvspots/models.py](https://github.com/andrewmarconi/generative-creative-lab/blob/main/src/cw/tvspots/models.py)
