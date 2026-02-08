# Implementation Plan: Model Refactoring

## Overview

This document provides step-by-step implementation details for Issue #46.

## Phase 1: Model Refactoring

### Step 1.1: Create Base AdUnit Model

**File:** `src/cw/tvspots/models.py`

```python
class AdUnit(models.Model):
    """Polymorphic base model for all ad unit types (video, audio, print, etc.)."""

    AD_UNIT_TYPE_CHOICES = [
        ("VIDEO", "Video"),
        ("AUDIO", "Audio"),  # Future
        ("PRINT", "Print"),  # Future
    ]

    ORIGIN_ADAPTATION_CHOICES = [
        ("ORIGIN", "Origin"),
        ("ADAPTATION", "Adaptation"),
        # Future: ("LOCALIZATION", "Localization"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        # Pipeline-specific statuses
        ("concept_analysis", "Concept Analysis"),
        ("cultural_analysis", "Cultural Analysis"),
        ("writing", "Writing"),
        ("cultural_evaluation", "Cultural Evaluation"),
        ("concept_evaluation", "Concept Evaluation"),
        ("revising", "Revising"),
    ]

    # Core fields
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="ad_units",
    )
    ad_unit_type = models.CharField(
        max_length=20,
        choices=AD_UNIT_TYPE_CHOICES,
        editable=False,  # Set automatically by child class
    )
    origin_or_adaptation = models.CharField(
        max_length=20,
        choices=ORIGIN_ADAPTATION_CHOICES,
        default="ORIGIN",
        help_text="Is this an origin or adapted version?",
    )
    code = models.CharField(
        max_length=50,
        help_text="Version code (e.g., 'US-EN-001', 'DE-DE-002')",
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descriptive title for this ad unit",
    )

    # Metadata (null/blank for ORIGIN units)
    region = models.ForeignKey(
        "core.Region",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target region (for adaptations)",
    )
    country = models.ForeignKey(
        "core.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target country (for adaptations)",
    )
    language = models.ForeignKey(
        "core.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target language (for adaptations)",
    )
    llm_model = models.ForeignKey(
        "core.LLMModel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Override language's primary LLM model",
    )

    # Pipeline data (for adapted units)
    use_pipeline = models.BooleanField(
        default=False,
        help_text="Use multi-agent pipeline for adaptation",
    )
    concept_brief = models.JSONField(
        null=True,
        blank=True,
        help_text="Concept extraction from pipeline",
    )
    cultural_brief = models.JSONField(
        null=True,
        blank=True,
        help_text="Cultural research from pipeline",
    )
    evaluation_history = models.JSONField(
        default=list,
        blank=True,
        help_text="Evaluation results from pipeline",
    )
    pipeline_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Pipeline timing and model info",
    )

    # Job tracking
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="completed",
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for async processing",
    )
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Adaptation chain tracking
    source_ad_unit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_units",
        help_text="Source ad unit this was adapted from",
    )

    class Meta:
        db_table = "tvspots_adunit"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "ad_unit_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.campaign.script_title} - {self.code}"

    @property
    def effective_llm_model(self):
        """Get LLM model (override or language default)."""
        return self.llm_model or (self.language.primary_model if self.language else None)
```

### Step 1.2: Create VideoAdUnit Model

**File:** `src/cw/tvspots/models.py`

```python
class VideoAdUnit(AdUnit):
    """Video-specific ad unit (merges TvSpotVersion + AdaptationJob + TVSpotAdaptation)."""

    duration = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Duration in seconds",
    )
    visual_style_prompt = models.TextField(
        blank=True,
        help_text="Common visual style applied to all script rows",
    )

    class Meta:
        db_table = "tvspots_videoadunit"
        verbose_name = "Video Ad Unit"
        verbose_name_plural = "Video Ad Units"

    def save(self, *args, **kwargs):
        # Automatically set ad_unit_type
        self.ad_unit_type = "VIDEO"
        super().save(*args, **kwargs)
```

### Step 1.3: Rename TvSpot to Campaign

**File:** `src/cw/tvspots/models.py`

```python
class Campaign(models.Model):
    """Top-level campaign container (formerly TvSpot)."""

    job_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal tracking ID",
    )
    script_title = models.CharField(
        max_length=200,
        help_text="Campaign/script title",
    )
    client_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200)
    product_name = models.CharField(max_length=200, blank=True)
    original_script_data = models.JSONField(
        help_text="Original script content as JSON",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tvspots_campaign"
        ordering = ["-created_at"]
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        return f"{self.client_name} - {self.script_title}"
```

### Step 1.4: Create AdUnitScriptRow

**File:** `src/cw/tvspots/models.py`

```python
class AdUnitScriptRow(models.Model):
    """Script row linked polymorphically to any AdUnit (formerly TvSpotScriptRow)."""

    ad_unit = models.ForeignKey(
        AdUnit,  # Points to base class - works with VideoAdUnit, AudioAdUnit, etc.
        on_delete=models.CASCADE,
        related_name="script_rows",
    )
    order_index = models.IntegerField(
        help_text="Row order (0-based)",
    )
    shot_number = models.CharField(
        max_length=10,
        blank=True,
        help_text="Shot/scene number",
    )
    timecode = models.CharField(
        max_length=20,
        blank=True,
        help_text="Timecode (HH:MM:SS:FF or HH:MM:SS.mmm)",
    )
    visual_text = models.TextField(
        help_text="Visual/video column content",
    )
    audio_text = models.TextField(
        blank=True,
        help_text="Audio/dialogue column content",
    )

    class Meta:
        db_table = "tvspots_adunitscriptrow"
        ordering = ["ad_unit", "order_index"]
        unique_together = [["ad_unit", "order_index"]]
        verbose_name = "Ad Unit Script Row"
        verbose_name_plural = "Ad Unit Script Rows"

    def __str__(self):
        return f"{self.ad_unit.code} - Row {self.order_index + 1}"
```

### Step 1.5: Rename StoryboardJob to Storyboard

**File:** `src/cw/tvspots/models.py`

```python
class Storyboard(models.Model):
    """Storyboard generation job (formerly StoryboardJob)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    video_ad_unit = models.ForeignKey(
        VideoAdUnit,  # Specific to video ad units
        on_delete=models.CASCADE,
        related_name="storyboards",
    )
    diffusion_model = models.ForeignKey(
        "diffusion.DiffusionModel",
        on_delete=models.PROTECT,
        related_name="storyboards",
    )
    lora_model = models.ForeignKey(
        "diffusion.LoraModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storyboards",
    )
    images_per_row = models.PositiveIntegerField(
        default=1,
        help_text="Number of images to generate per script row",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tvspots_storyboard"
        ordering = ["-created_at"]
        verbose_name = "Storyboard"
        verbose_name_plural = "Storyboards"

    def __str__(self):
        return f"Storyboard for {self.video_ad_unit.code} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def total_jobs(self):
        """Total DiffusionJobs in this storyboard."""
        return self.images.count()

    @property
    def completed_jobs(self):
        """Completed DiffusionJobs."""
        return self.images.filter(
            diffusion_job__status="completed"
        ).count()
```

### Step 1.6: Update StoryboardImage

**File:** `src/cw/tvspots/models.py`

```python
class StoryboardImage(models.Model):
    """Links storyboard to individual diffusion jobs."""

    storyboard = models.ForeignKey(
        Storyboard,
        on_delete=models.CASCADE,
        related_name="images",
    )
    script_row = models.ForeignKey(
        AdUnitScriptRow,
        on_delete=models.CASCADE,
        related_name="storyboard_images",
    )
    diffusion_job = models.OneToOneField(
        "diffusion.DiffusionJob",
        on_delete=models.CASCADE,
        related_name="storyboard_image",
    )
    image_index = models.IntegerField(
        help_text="Image number for this script row (0-based)",
    )

    class Meta:
        db_table = "diffusion_storyboardimage"
        ordering = ["storyboard", "script_row__order_index", "image_index"]
        unique_together = [["storyboard", "script_row", "image_index"]]
        verbose_name = "Storyboard Image"
        verbose_name_plural = "Storyboard Images"

    def __str__(self):
        return f"{self.storyboard} - Row {self.script_row.order_index} - Image {self.image_index}"
```

## Phase 2: Admin Updates

### Step 2.1: Campaign Admin

**File:** `src/cw/tvspots/admin.py`

Update `TvSpotAdmin` → `CampaignAdmin`:
- Update model reference
- Remove `created_at`, `updated_at` from `list_display`
- Update verbose names

### Step 2.2: VideoAdUnit Admin

**File:** `src/cw/tvspots/admin.py`

Merge `TvSpotVersionAdmin`, `AdaptationJobAdmin`, `TVSpotAdaptationAdmin` → `VideoAdUnitAdmin`:
- Combine all list displays (remove timestamps)
- Merge fieldsets
- Combine admin actions
- Update filters for new field names

### Step 2.3: AdUnitScriptRow Admin

**File:** `src/cw/tvspots/admin.py`

Rename `TvSpotScriptRowAdmin` → `AdUnitScriptRowAdmin`:
- Update FK references
- Keep inline for VideoAdUnit admin

### Step 2.4: Storyboard Admin

**File:** `src/cw/tvspots/admin.py`

Rename `StoryboardJobAdmin` → `StoryboardAdmin`:
- Update model references
- Remove timestamps from list_display
- Update FK references to VideoAdUnit

## Phase 3: Task Updates

### Step 3.1: Update create_adaptation_task

**File:** `src/cw/tvspots/tasks.py`

- Change from creating `TvSpotVersion` to updating `VideoAdUnit` fields
- Update all references to use new model names

### Step 3.2: Update generate_storyboard_task

**File:** `src/cw/tvspots/tasks.py`

- Change `StoryboardJob` → `Storyboard`
- Update `TvSpotVersion` → `VideoAdUnit`
- Update script row references

### Step 3.3: Update Pipeline Nodes

**File:** `src/cw/lib/pipeline/nodes.py`

- Update model imports
- Change references from `AdaptationJob` to `VideoAdUnit`

## Phase 4: Database Migration

### Step 4.1: Delete Old Migrations

```bash
rm -rf src/cw/tvspots/migrations/
mkdir src/cw/tvspots/migrations/
touch src/cw/tvspots/migrations/__init__.py
```

### Step 4.2: Create Fresh Migration

```bash
uv run manage.py makemigrations tvspots
```

### Step 4.3: Apply Migration

```bash
uv run manage.py migrate
```

## Phase 5: Cleanup

### Step 5.1: Update CLAUDE.md

Update documentation with new model structure.

### Step 5.2: Update Docstrings

Ensure all docstrings reference new model names.

### Step 5.3: Remove Deprecated Imports

Search for and remove:
- `TvSpot` imports (replace with `Campaign`)
- `TvSpotVersion` imports (replace with `VideoAdUnit`)
- `AdaptationJob` imports (replace with `VideoAdUnit`)
- `Market`, `AdaptationMarket` imports (delete)

## Testing Checklist

- [ ] Can create Campaign
- [ ] Can create origin VideoAdUnit
- [ ] Can create adaptation VideoAdUnit via admin action
- [ ] Can create Storyboard for VideoAdUnit
- [ ] Storyboard generates images correctly
- [ ] Pipeline workflow works with VideoAdUnit
- [ ] Admin list views load without errors
- [ ] Admin filters work correctly
- [ ] All Celery tasks complete successfully

## Rollback Plan

If issues arise, rollback steps:
1. `git revert` the refactoring commit
2. Restore previous migrations
3. `manage.py migrate tvspots <previous_migration>`
4. Restart Django/Celery workers

## Success Metrics

- Zero migration errors
- All admin pages load successfully
- Tasks create correct model instances
- No broken foreign key references
- Clean git diff (all old model references removed)
