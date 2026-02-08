# Issue #46: Refactor TV Spot Models for Cleaner Domain Model

**Status:** Planning
**Type:** Refactoring
**Priority:** High
**Created:** 2026-02-07

## Problem Statement

The current TV Spot model architecture has become fragmented and confusing:
- Multiple overlapping models (`TvSpot`, `TvSpotVersion`, `AdaptationJob`, `TVSpotAdaptation`)
- Unclear separation of concerns between job tracking and content storage
- Inconsistent naming (e.g., "TvSpot" shown as "TVC Project" in admin)
- Market-based model that's being deprecated
- Not extensible to other ad formats (audio, print, etc.)

## Goals

1. **Simplify the model hierarchy** - Clear parent-child relationships
2. **Consistent naming** - Models match their domain purpose
3. **Future-proof** - Support for video, audio, print ad units
4. **Clean separation** - Merge job tracking into content models (like `StoryboardJob` pattern)
5. **Remove deprecated concepts** - Eliminate `Market` and `AdaptationMarket`

## Proposed Architecture

```
Campaign (formerly TvSpot)
└─ AdUnit (abstract polymorphic base)
   └─ VideoAdUnit (concrete, merges TvSpotVersion + AdaptationJob + TVSpotAdaptation)
      ├─ AdUnitScriptRow (formerly TvSpotScriptRow) - O2M
      └─ Storyboard (formerly StoryboardJob) - O2M
         └─ StoryboardImage - O2M
            └─ DiffusionJob - FK
```

### Model Summary

| New Model | Replaces | Purpose |
|-----------|----------|---------|
| `Campaign` | `TvSpot` | Top-level campaign container |
| `AdUnit` | *(new)* | Polymorphic base for all ad unit types |
| `VideoAdUnit` | `TvSpotVersion` + `AdaptationJob` + `TVSpotAdaptation` | Video ad unit with job tracking |
| `AdUnitScriptRow` | `TvSpotScriptRow` | Script rows (polymorphic link to any ad unit) |
| `Storyboard` | `StoryboardJob` | Storyboard generation job |

### Removed Models
- ❌ `TvSpot` (renamed to `Campaign`)
- ❌ `TvSpotVersion` (merged into `VideoAdUnit`)
- ❌ `AdaptationJob` (merged into `VideoAdUnit`)
- ❌ `TVSpotAdaptation` (merged into `VideoAdUnit`)
- ❌ `TvSpotScriptRow` (renamed to `AdUnitScriptRow`)
- ❌ `StoryboardJob` (renamed to `Storyboard`)
- ❌ `Market` (deleted completely)
- ❌ `AdaptationMarket` (deleted completely)

## Implementation Plan

See [implementation_plan.md](./implementation_plan.md) for detailed steps.

## Key Design Decisions

### 1. Polymorphic Ad Units via Multi-Table Inheritance

**Decision:** Use Django's multi-table inheritance for ad unit types.

**Rationale:**
- Natural IS-A relationship (VideoAdUnit IS-A AdUnit)
- Database-level foreign key constraints
- Clean ORM patterns
- Easy to extend (AudioAdUnit, PrintAdUnit, etc.)

**Trade-offs:**
- Extra JOIN when accessing child-specific fields (acceptable)
- Two database tables per child type (acceptable for data integrity)

### 2. Merge Job Tracking into Content Model

**Decision:** VideoAdUnit contains both content and job tracking (status, celery_task_id, error_message).

**Rationale:**
- Follows `StoryboardJob` pattern already in codebase
- Simpler than separate job tracker + result model
- Single source of truth
- Easier queries

**Trade-offs:**
- Mixed concerns (acceptable - job state is part of the ad unit lifecycle)

### 3. Metadata on VideoAdUnit (not Campaign)

**Decision:** Region, country, language live on `VideoAdUnit`, not `Campaign`.

**Rationale:**
- Each adaptation targets different markets
- Origin units don't have metadata (null/blank)
- Adaptations have specific market context

### 4. Greenfield Migration

**Decision:** Fresh start with new migrations, no data migration from old models.

**Rationale:**
- Reduces complexity
- Clean slate for improved architecture
- Current system is in development/testing phase

## Success Criteria

- [ ] All models follow new naming convention
- [ ] Single clear hierarchy: Campaign → VideoAdUnit → Script/Storyboard
- [ ] Market model completely removed
- [ ] Admin interfaces updated with clean list views (no created_at/updated_at)
- [ ] Tasks work with new model structure
- [ ] Ready to extend to AudioAdUnit, PrintAdUnit

## Timeline

**Estimated effort:** 1-2 sessions

1. **Phase 1:** Model refactoring (30-45 min)
2. **Phase 2:** Admin updates (30 min)
3. **Phase 3:** Task updates (20 min)
4. **Phase 4:** Testing & cleanup (15 min)

## References

- Original discussion: Session 2026-02-07
- Related: Issue #44 (Region/Country/Language refactoring)
- Related: Issue #45 (Brand Agent - will use new VideoAdUnit model)

## Notes

- **StoryboardJob pattern:** This refactor extends the pattern established by `StoryboardJob`, which successfully merges job tracking with the core model.
- **Future extensions:** Framework ready for `AudioAdUnit` (radio spots), `PrintAdUnit` (magazine/newspaper), `SocialAdUnit` (social media), etc.
- **Admin UX:** All list views cleaned up by removing timestamp columns for better readability.
