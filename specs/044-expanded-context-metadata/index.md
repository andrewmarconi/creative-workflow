# 044 Expanded Context Metadata

- **Status:** Design Complete, Ready for Implementation
- **Created:** 2026-02-06
- **Issue:** [#44](https://github.com/andrewmarconi/generative-creative-lab/issues/44)

## 📋 Documentation Index

This specification suite provides comprehensive documentation for refactoring the TV spot adaptation system to use multi-dimensional reference data with compositional insights.

### Core Documents

```{toctree}
:maxdepth: 1
:glob:

*
```

1. **[PRD (Product Requirements Document)](./prd.md)** - *Start here*
   - Executive summary and problem statement
   - User stories and acceptance criteria
   - Goals, non-goals, and success metrics
   - High-level solution overview

2. **[Data Model](./data_model.md)** - *Technical design*
   - Complete ER diagram (Mermaid)
   - Detailed model definitions
   - Relationships and constraints
   - Query examples and indexing strategy

3. **[Default Data](./default_data.md)** - *Reference data*
   - Starter regions, countries, languages, cultures
   - Comprehensive insights at all levels
   - M2M relationship mappings
   - Import command specification

4. **[Implementation Plan](./implementation_plan.md)** - *Execution roadmap*
   - 6-phase implementation timeline
   - Task breakdowns per phase
   - Deliverables and testing strategy
   - Rollout and deployment plan

5. **[Migration Strategy](./migration_strategy.md)** - *Critical data migration*
   - TvSpotVersion.language CharField → FK migration
   - 5-step migration process with validation
   - Rollback procedures
   - Pre/post-migration testing

6. **[Insights Composition](./insights_composition.md)** - *Feature deep-dive*
   - How insights cascade (Region → Country → Language → Market)
   - Composition logic and implementation
   - Template integration examples
   - Benefits and testing strategy

---

## 🎯 Quick Start

### For Product/Business Stakeholders

**Read:** [PRD](./prd.md)

**Key Takeaways:**
- Solve real-world adaptation patterns (Nordics → multi-language, Canada bilingual)
- Eliminate duplicated cultural insights across markets
- Better language support with locale codes (en-US vs en-CA)
- Flexible dimensional tagging (region, country, language, culture)

### For Engineers

**Read:** [Data Model](./data_model.md) → [Implementation Plan](./implementation_plan.md)

**Key Takeaways:**
- 4 new core models: Region, Country, Culture, Language (enhanced)
- TvSpotVersion.language becomes ForeignKey (breaking change)
- Multi-level insights compose hierarchically
- 6-week phased implementation

### For QA/Testing

**Read:** [Migration Strategy](./migration_strategy.md) → [Implementation Plan](./implementation_plan.md)

**Focus On:**
- Zero data loss during language CharField → FK migration
- Validation at each migration step
- Pre/post-migration test scenarios
- Rollback procedures

### For Localization Specialists

**Read:** [Default Data](./default_data.md) → [Insights Composition](./insights_composition.md)

**Key Benefits:**
- Language-specific insights (Quebec French vs France French)
- Country regulations (Bill 96, GDPR, etc.)
- Cultural patterns (Nordic minimalism, Latin warmth)
- No more duplicated guidance across markets

---

## 🏗️ Architecture Overview

### Current State (Before)

```
AdaptationMarket (all insights stored here)
  ↓
TvSpotVersion
  - language: CharField("en-US", "fr-CA", etc.)
```

**Problems:**
- ❌ Duplicate insights across related markets
- ❌ No language variant grouping or model associations
- ❌ Cannot model regional → country → language cascades
- ❌ No reusability of linguistic/regulatory guidance

### Target State (After)

```
Region (cultural patterns)
  ↓
Country (regulations + local culture)
  ↓
Language (linguistic rules) ← LLMModel associations
  ↓
Market (campaign positioning)
  ↓
TvSpotVersion
  - language: ForeignKey(Language)
```

**Benefits:**
- ✅ Insights at appropriate level (no duplication)
- ✅ Compositional guidance (region + country + language + market)
- ✅ Locale-aware languages with model recommendations
- ✅ Flexible dimensional tagging

---

## 📊 Data Model Highlights

### New Models

| Model | Purpose | Example |
|-------|---------|---------|
| **Region** | Cultural/market grouping | North America, Nordics, DACH |
| **Country** | Political/regulatory entity | USA, Canada, Sweden, Switzerland |
| **Culture** | Cultural theme/characteristic | Nordic Minimalism, Germanic Formality |
| **Language** | Locale-specific variant | en-US, fr-CA, de-CH, es-MX |

### Key Relationships

- **Country** ↔ **Region** (M2M): Switzerland in both DACH and EU-WEST
- **Country** ↔ **Language** (M2M with `is_primary`): Canada has en-CA (primary), fr-CA
- **Language** → **LLMModel**: Recommendations for text generation
- **Region** ↔ **Culture** (M2M): Nordics associated with "Nordic Minimalism"

### Insights Cascade

All models have `insights` JSONField:

```
Region.insights (broad)
  ↓
Country.insights (regulations)
  ↓
Language.insights (linguistic)
  ↓
Market.insights (campaign-specific)
```

Compose when generating adaptations → comprehensive, non-duplicated guidance.

---

## 🚀 Implementation Timeline

| Phase | Duration | Focus | Deliverable |
|-------|----------|-------|-------------|
| **1** | Week 1-2 | Core models + seed data | ✅ Models in DB, reference data loaded |
| **2** | Week 2-3 | Admin UI updates | ✅ Admin for managing reference data |
| **3** | Week 3-4 | Language FK migration | ✅ TvSpotVersion.language is FK |
| **4** | Week 4-5 | Library code refactoring | ✅ adaptation.py, pipeline updated |
| **5** | Week 5-6 | TVSpotAdaptation (optional) | ✅ New flat adaptation model |
| **6** | Week 6 | Testing + deployment | ✅ Production deployment |

**Critical Path:** Phase 3 (Language migration) is the breaking change. All preparation in Phases 1-2.

---

## 🎓 Example: Quebec French Adaptation

### Input Configuration

```
Region: North America (optional)
Country: Canada
Language: fr-CA (Quebec French)
Market: "Quebec Premium Consumers"
```

### Composed Insights

The system automatically composes insights from all levels:

**Regional (North America):**
- Direct, benefit-oriented messaging
- Aspirational optimism themes

**Country (Canada):**
- Bill 96: French text ≥2x English size
- CASL requires opt-in for emails
- Québécois vs European French identity

**Language (fr-CA):**
- Vocabulary: 'char' not 'voiture', 'déjeuner' not 'petit-déjeuner'
- MUST use Quebec VO talent (distinct pronunciation)
- Informal 'tu' acceptable in advertising

**Market (Quebec Premium):**
- Emphasize quality over price
- Cultural pride themes resonate
- Environmental sustainability important

**Result:** Comprehensive guidance without duplication across Quebec markets.

---

## ✅ Success Criteria

### Immediate (Week 1-2)
- [ ] All core models created and seeded
- [ ] Import/export commands working
- [ ] Admin UI functional

### Short-term (Week 3-4)
- [ ] TvSpotVersion.language migrated to FK
- [ ] 100% data migration success rate
- [ ] All library code updated

### Long-term (Month 1-3)
- [ ] 60%+ reduction in duplicated insights
- [ ] 80%+ of adaptations use dimensional tagging
- [ ] Query performance <100ms for regional rollups
- [ ] Positive user feedback

---

## 🔐 Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | 🔴 High | Multi-step migration with backups; validation at each step |
| Unmapped language codes | 🟡 Medium | Pre-migration audit; manual mapping for edge cases |
| Performance degradation | 🟡 Medium | Proper indexing; select_related/prefetch_related |
| Breaking workflows | 🟡 Medium | Parallel deployment; feature flags |

**Rollback Plan:** Documented at each migration step. Restore from backup if critical issues.

---

## 📚 Related Issues

- **[Issue #26](https://github.com/andrewmarconi/generative-creative-lab/tree/main/specs/026_multi_model_pipeline_adaptations/prd.md)** - Multi-Model Pipeline (uses language data)
- **[Issue #45](https://github.com/andrewmarconi/generative-creative-lab/issues/45)** - BrandAgent for brand consistency

---

## 👥 Stakeholders

- **Product:** Expanded capabilities, better UX
- **Engineering:** Cleaner architecture, less duplication
- **Localization:** Language-specific guidance, no more copy-paste
- **Creative:** Better market insights, cultural awareness

---

## 🔗 Quick Links

- [GitHub Issue #44](https://github.com/andrewmarconi/generative-creative-lab/issues/44)
- [Current Implementation](https://github.com/andrewmarconi/generative-creative-lab/blob/main/src/cw/tvspots/models.py)
- [Core Models](https://github.com/andrewmarconi/generative-creative-lab/blob/main/src/cw/core/models.py)
- [Adaptation Library](https://github.com/andrewmarconi/generative-creative-lab/blob/main/src/cw/lib/adaptation.py)

---

## 📝 Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-06 | Initial specification suite created | Claude (via andrewmarconi) |

---

## ❓ Questions?

For questions or clarifications:
1. Review the [PRD](./prd.md) for high-level overview
2. Check [Data Model](./data_model.md) for technical details
3. See [Implementation Plan](./implementation_plan.md) for execution

**Next Steps:** Review with team → Approve design → Begin Phase 1 implementation
