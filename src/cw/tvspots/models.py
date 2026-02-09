from django.db import models


class Campaign(models.Model):
    """Top-level campaign container (formerly TvSpot).

    Represents a campaign/project before any adaptations or storyboard generation.
    Created via JSON import (management command or admin action).
    """

    job_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal tracking ID (e.g., 'ACME-2024-001')",
    )
    script_title = models.CharField(
        max_length=200,
        help_text="Campaign/script title",
    )
    client_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
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


class AdUnit(models.Model):
    """Polymorphic base model for all ad unit types (video, audio, print, etc.).

    Uses Django multi-table inheritance. Child models (VideoAdUnit, AudioAdUnit, etc.)
    extend this base with media-specific fields.
    """

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
        # Pipeline-specific statuses (present tense - what's happening now)
        ("concept_analysis", "Analyzing Concept"),
        ("cultural_analysis", "Researching Culture"),
        ("writing", "Writing Script"),
        ("format_evaluation", "Evaluating Format"),
        ("cultural_evaluation", "Evaluating Culture"),
        ("concept_evaluation", "Evaluating Concept"),
        ("revising", "Revising Script"),
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

    # Audience targeting
    persona = models.ForeignKey(
        "audiences.Persona",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target audience persona",
    )

    # Geographic metadata (synced from persona if set, or set independently)
    region = models.ForeignKey(
        "audiences.Region",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target region (for adaptations)",
    )
    country = models.ForeignKey(
        "audiences.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Target country (for adaptations)",
    )
    language = models.ForeignKey(
        "audiences.Language",
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


class VideoAdUnit(AdUnit):
    """Video-specific ad unit (merges TvSpotVersion + AdaptationJob + TVSpotAdaptation).

    Represents a video ad with script rows and optional storyboards. Can be either
    an origin unit or an adaptation targeting specific markets.
    """

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


class AdUnitScriptRow(models.Model):
    """Script row linked polymorphically to any AdUnit (formerly TvSpotScriptRow).

    Points to base AdUnit class, which allows script rows to work with VideoAdUnit,
    AudioAdUnit, PrintAdUnit, etc. via multi-table inheritance.
    """

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


class Storyboard(models.Model):
    """Storyboard generation job (formerly StoryboardJob).

    One Storyboard creates one DiffusionJob per script row (times images_per_row).
    Multiple Storyboards can exist per VideoAdUnit (different configs).
    """

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

    @property
    def progress_percent(self):
        """Completion percentage."""
        total = self.total_jobs
        if total == 0:
            return 0
        return int((self.completed_jobs / total) * 100)


class StoryboardImage(models.Model):
    """Links storyboard to individual diffusion jobs.

    Allows multiple images per row and multiple storyboard runs per video ad unit.
    """

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
        db_table = "tvspots_storyboardimage"
        ordering = ["storyboard", "script_row__order_index", "image_index"]
        unique_together = [["storyboard", "script_row", "image_index"]]
        verbose_name = "Storyboard Image"
        verbose_name_plural = "Storyboard Images"

    def __str__(self):
        return f"{self.storyboard} - Row {self.script_row.order_index} - Image {self.image_index}"
