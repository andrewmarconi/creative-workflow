# Implementation Plan

**Issue:** #44
**Last Updated:** 2026-02-06

---

## Overview

Phased implementation strategy to refactor the TV spot adaptation system from a simple market-based model to a multi-dimensional reference data system with compositional insights.

---

## Implementation Phases

### **Phase 1: Core Models & Infrastructure** (Week 1-2)

#### Tasks

1. **Create Core Models**
   - [ ] Add `Region`, `Country`, `Culture` models to `src/cw/core/models.py`
   - [ ] Update `Language` model with locale codes and `base_language` field
   - [ ] Add `insights` JSONField to Region, Country, Language
   - [ ] Create M2M through tables: `CountryRegion`, `CountryLanguage`, `RegionCulture`

2. **Create Initial Migrations**
   - [ ] Generate migration for new core models
   - [ ] Add indexes for common queries (base_language, is_active)
   - [ ] **Do NOT migrate TvSpotVersion.language yet** (Phase 3)

3. **Seed Reference Data**
   - [ ] Create `data/reference_data.json` with default regions/countries/languages/cultures
   - [ ] Create management command `import_reference_data`
   - [ ] Test import on clean database
   - [ ] Verify M2M relationships created correctly

**Deliverables:**
- ✅ New models in database
- ✅ Seeded with default reference data
- ✅ Import command working

**Testing:**
```bash
# Create fresh test DB
uv run manage.py migrate
uv run manage.py import_reference_data --dry-run
uv run manage.py import_reference_data

# Verify
uv run manage.py shell
>>> from cw.core.models import Region, Country, Language
>>> Region.objects.count()  # Should be 6
>>> Country.objects.count()  # Should be ~15
>>> Language.objects.filter(base_language='fr').count()  # Should be 4 (fr-FR, fr-CA, fr-BE, fr-CH)
```

---

### **Phase 2: Admin UI Updates** (Week 2-3)

#### Tasks

1. **Create Admin Interfaces for New Models**
   - [ ] `RegionAdmin` with insights display/editing
   - [ ] `CountryAdmin` with M2M inline for regions/languages
   - [ ] `CultureAdmin`
   - [ ] Update `LanguageAdmin` to show insights, base_language grouping

2. **Update AdaptationMarket Admin**
   - [ ] Add M2M fields for regions, countries, cultures
   - [ ] Rename `rules` to `insights` for consistency (or keep for compatibility)
   - [ ] Add inline displays for dimensional relationships

3. **Update TvSpot Adaptation Creation UI**
   - [ ] **Keep existing workflow** (no breaking changes yet)
   - [ ] Add preview of new language selector (read-only for now)
   - [ ] Show recommended languages based on market's countries

4. **Create Export Command**
   - [ ] `export_reference_data` management command
   - [ ] Mirror structure of `import_reference_data`

**Deliverables:**
- ✅ Admin UI for managing reference data
- ✅ No breaking changes to existing adaptation workflow
- ✅ Export command for backing up reference data

**Testing:**
```bash
# Admin access
# Navigate to /admin/core/region/
# Create test region with insights
# Assign countries to region via M2M
# Export and verify JSON structure
uv run manage.py export_reference_data > test_export.json
```

---

### **Phase 3: TvSpotVersion Language Migration** (Week 3-4)

**CRITICAL: This is the breaking change phase**

#### Tasks

1. **Create Backwards-Compatible Language Lookup**
   ```python
   # In migration
   def migrate_language_codes(apps, schema_editor):
       TvSpotVersion = apps.get_model('tvspots', 'TvSpotVersion')
       Language = apps.get_model('core', 'Language')

       for version in TvSpotVersion.objects.all():
           lang_code = version.language  # Old CharField value
           try:
               language = Language.objects.get(code=lang_code)
               version.language_new = language  # Temp FK field
               version.save()
           except Language.DoesNotExist:
               # Log unmapped codes for manual review
               print(f"WARNING: No Language found for code '{lang_code}' (TvSpotVersion #{version.pk})")
   ```

2. **Multi-Step Migration Strategy**
   - [ ] **Migration 1**: Add `language_new` ForeignKey field (nullable)
   - [ ] **Migration 2**: Run data migration to populate `language_new` from `language` CharField
   - [ ] **Migration 3**: Verify all records migrated (check for NULLs)
   - [ ] **Migration 4**: Drop old `language` CharField
   - [ ] **Migration 5**: Rename `language_new` → `language`

3. **Update TvSpotVersion Model**
   ```python
   class TvSpotVersion(models.Model):
       # ...
       language = models.ForeignKey(  # CHANGED from CharField
           'core.Language',
           on_delete=models.PROTECT,
           related_name='tvspot_versions',
           help_text="Language for this version (e.g., en-US, fr-CA)"
       )
   ```

4. **Rollback Plan**
   - [ ] Tag current production state before deploying
   - [ ] Keep backup of `language` CharField values in separate table
   - [ ] Document rollback procedure

**Deliverables:**
- ✅ TvSpotVersion.language is ForeignKey
- ✅ All existing data migrated
- ✅ No data loss

**Testing:**
```bash
# Pre-migration checks
uv run manage.py shell
>>> from cw.tvspots.models import TvSpotVersion
>>> unmapped = TvSpotVersion.objects.exclude(language__in=['en-US', 'fr-CA', ...])
>>> print(f"Unmapped language codes: {set(unmapped.values_list('language', flat=True))}")

# Run migrations
uv run manage.py migrate

# Post-migration verification
>>> TvSpotVersion.objects.filter(language__isnull=True).count()  # Should be 0
>>> TvSpotVersion.objects.first().language  # Should return Language object
```

---

### **Phase 4: Library Code Refactoring** (Week 4-5)

#### Tasks

1. **Update `adaptation.py`**
   - [ ] Change `origin_version.language` (string) → `origin_version.language.code` (FK)
   - [ ] Update prompt building to use Language.insights
   - [ ] Test single-step adaptation path

2. **Update Pipeline Code**
   - [ ] `src/cw/lib/pipeline/state.py`: Update `build_initial_state()` to use FK
   - [ ] Add insights composition helper: `get_composite_insights()`
   - [ ] Update prompt templates to include regional/country/language insights

3. **Update Management Commands**
   - [ ] `import_tvspot.py`: Look up Language FK instead of storing string
   - [ ] `import_markets.py`: Support new insights structure
   - [ ] `export_markets.py`: Export with dimensional relationships

4. **Create Insights Composition Helper**
   ```python
   # src/cw/lib/insights.py
   def compose_insights(adaptation_job):
       """Aggregate insights from region → country → language → market."""
       insights = []

       if adaptation_job.region:
           insights.append({
               'source': f'Region: {adaptation_job.region.name}',
               'markdown': adaptation_job.region.insights_as_markdown()
           })

       if adaptation_job.country:
           insights.append({
               'source': f'Country: {adaptation_job.country.name}',
               'markdown': adaptation_job.country.insights_as_markdown()
           })

       language = adaptation_job.effective_language
       insights.append({
           'source': f'Language: {language.name}',
           'markdown': language.insights_as_markdown()
       })

       insights.append({
           'source': f'Market: {adaptation_job.target_market.name}',
           'markdown': adaptation_job.target_market.rules_as_markdown()
       })

       return insights
   ```

**Deliverables:**
- ✅ All library code uses Language FK
- ✅ Insights composition working
- ✅ Management commands updated

**Testing:**
```bash
# Test adaptation with insights composition
uv run manage.py shell
>>> from cw.tvspots.models import AdaptationJob
>>> job = AdaptationJob.objects.last()
>>> from cw.lib.insights import compose_insights
>>> insights = compose_insights(job)
>>> for section in insights:
...     print(f"\n## {section['source']}")
...     print(section['markdown'])
```

---

### **Phase 5: TVSpotAdaptation Model (Optional)** (Week 5-6)

**Note:** This is the new flat adaptation model from issue #44. Can be deferred if TvSpotVersion refactoring is sufficient.

#### Tasks

1. **Create TVSpotAdaptation Model**
   ```python
   class TVSpotAdaptation(models.Model):
       job_id = models.CharField(max_length=100, unique=True)
       title = models.CharField(max_length=200)
       source_adaptation = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
       region = models.ForeignKey(Region, null=True, blank=True, on_delete=models.PROTECT)
       country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.PROTECT)
       language = models.ForeignKey(Language, null=True, blank=True, on_delete=models.PROTECT)
       cultures = models.ManyToManyField(Culture, blank=True)
       adaptation_notes = models.TextField(blank=True)
       script_data = models.JSONField()
       # ...
   ```

2. **Admin Interface**
   - [ ] Create `TVSpotAdaptationAdmin` with dimensional filtering
   - [ ] Add actions: "Create child adaptation", "View adaptation chain"

3. **Migration Path from TvSpotVersion**
   - [ ] Decide: Parallel models or migrate existing?
   - [ ] If parallel: Create sync mechanism
   - [ ] If migration: Data migration script

**Deliverables:**
- ✅ New flexible adaptation model
- ✅ Admin UI for managing adaptations
- ✅ Documentation on when to use TvSpotVersion vs TVSpotAdaptation

---

### **Phase 6: Testing & Validation** (Week 6)

#### Tasks

1. **Unit Tests**
   - [ ] Test Language.get_all_models()
   - [ ] Test Country.get_primary_languages()
   - [ ] Test insights_as_markdown() for all models
   - [ ] Test compose_insights() helper

2. **Integration Tests**
   - [ ] Test full adaptation flow with new Language FK
   - [ ] Test pipeline with insights composition
   - [ ] Test import/export commands with full dataset

3. **Admin UI Tests**
   - [ ] Test creating Region with insights
   - [ ] Test assigning languages to countries via M2M
   - [ ] Test adaptation creation with language selection

4. **Data Integrity Tests**
   - [ ] Verify no orphaned Language references
   - [ ] Verify M2M relationships intact
   - [ ] Verify insights JSON structure valid

**Deliverables:**
- ✅ Comprehensive test suite
- ✅ All tests passing
- ✅ Test coverage report

---

## Rollout Strategy

### Development Environment

1. Deploy to dev environment
2. Run full test suite
3. Manual QA of admin UI
4. Test adaptation creation end-to-end

### Staging Environment

1. Copy production data to staging
2. Run migrations (read-only first)
3. Verify data integrity
4. Test rollback procedure
5. Performance testing (query times, M2M joins)

### Production Deployment

1. **Pre-deployment**
   - [ ] Database backup
   - [ ] Tag current codebase version
   - [ ] Notify team of maintenance window

2. **Deployment**
   - [ ] Put app in maintenance mode
   - [ ] Run migrations (phases 1-3)
   - [ ] Import reference data
   - [ ] Deploy new code
   - [ ] Verify basic functionality
   - [ ] Exit maintenance mode

3. **Post-deployment**
   - [ ] Monitor error logs
   - [ ] Verify adaptation jobs running
   - [ ] Check admin UI accessibility
   - [ ] Test creating new adaptations

4. **Rollback Criteria**
   - Data loss detected
   - Critical errors in adaptation flow
   - Admin UI inaccessible
   - Performance degradation >50%

---

## Success Metrics

### Immediate (Week 1-2)

- [ ] All core models created and seeded
- [ ] Import command working
- [ ] Admin UI accessible

### Short-term (Week 3-4)

- [ ] TvSpotVersion.language migrated to FK
- [ ] 100% data migration success rate
- [ ] All library code updated

### Long-term (Month 1-3)

- [ ] 60%+ reduction in duplicated insights
- [ ] 80%+ of new adaptations use dimensional tagging
- [ ] Query performance <100ms for regional rollups
- [ ] Positive user feedback from localization team

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Data loss during migration** | Multi-step migration with backups at each step; rollback plan |
| **Unmapped language codes** | Pre-migration audit; manual mapping for edge cases |
| **Performance degradation** | Proper indexing; select_related/prefetch_related; query profiling |
| **Breaking existing workflows** | Parallel deployment; feature flags for new UI |
| **Reference data gaps** | Comprehensive default data; easy import process |

---

## Dependencies

### External

- ✅ Django 5.x migrations support
- ✅ PostgreSQL JSON field support
- ✅ Python 3.12+ (for typing support)

### Internal

- ✅ Issue #26 multi-model pipeline (uses language data)
- ⚠️ Any external systems consuming TvSpotVersion data (API, exports)

---

## References

- [PRD](./prd.md)
- [Data Model](./data_model.md)
- [Default Data](./default_data.md)
- [Migration Strategy](./migration_strategy.md)
- [Insights Composition](./insights_composition.md)
