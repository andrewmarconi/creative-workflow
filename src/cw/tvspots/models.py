from django.db import models


class Brand(models.Model):
    """Brand reference data with voice, values, and visual guidelines.

    Applied to a Campaign as the primary brand. Can be overridden per
    VideoAdUnit for market-specific trade names (e.g., Lay's → Walkers).
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Short code (e.g., 'LAYS', 'WALKERS', 'PEPSI')",
    )
    name = models.CharField(
        max_length=200,
        help_text="Display name (e.g., 'Lay's', 'Walkers')",
    )
    description = models.TextField(
        blank=True,
        help_text="Brand overview and positioning",
    )
    guidelines = models.TextField(
        blank=True,
        help_text="Brand voice, values, visual identity, and messaging guidelines",
    )
    insights = models.JSONField(
        default=list,
        blank=True,
        help_text="Brand-specific patterns: [{heading, points[]}]",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tvspots_brand"
        ordering = ["name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return f"{self.name} ({self.code})"


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
    product_name = models.CharField(max_length=200, blank=True)
    brand = models.ForeignKey(
        "Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
        help_text="Primary brand for this campaign",
    )
    original_script_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Original script content as JSON (optional, generated from video if not provided)",
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
        ("brand_evaluation", "Evaluating Brand"),
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
    brand = models.ForeignKey(
        "tvspots.Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ad_units",
        help_text="Brand override for market-specific trade names",
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
    pipeline_model_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-node LLM model overrides: {node_key: llm_model_pk}",
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

    @property
    def effective_brand(self):
        """Get brand (ad unit override or campaign default)."""
        return self.brand or self.campaign.brand


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


class AdUnitMedia(models.Model):
    """Uploaded video file for origin script extraction.

    Tracks video upload status and processing lifecycle. Once processing
    completes, can be converted into an origin VideoAdUnit.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Upload"),
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("reviewed", "Reviewed"),
    ]

    # Core fields
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="ad_unit_media",
        help_text="Campaign this media belongs to",
    )
    video_file = models.FileField(
        upload_to="ad_unit_media/%Y/%m/",
        help_text="Uploaded MP4 video file",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    # Video metadata (extracted from file)
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration in seconds",
    )
    resolution_width = models.IntegerField(null=True, blank=True)
    resolution_height = models.IntegerField(null=True, blank=True)
    frame_rate = models.FloatField(null=True, blank=True)
    audio_channels = models.IntegerField(null=True, blank=True)
    audio_sample_rate = models.IntegerField(null=True, blank=True)
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Size in bytes",
    )

    # Processing tracking
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for async video processing",
    )
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)

    # Results reference
    result = models.OneToOneField(
        "VideoProcessingResult",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media",
        help_text="Processing results (scenes, script, etc.)",
    )

    # Generated AdUnit (once reviewed/approved)
    video_ad_unit = models.OneToOneField(
        "VideoAdUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_media",
        help_text="Origin VideoAdUnit created from this media",
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tvspots_adunitmedia"
        ordering = ["-created_at"]
        verbose_name = "Ad Unit Media"
        verbose_name_plural = "Ad Unit Media"

    def __str__(self):
        return f"Ad Unit Media for {self.campaign} ({self.status})"

    def save(self, *args, **kwargs):
        """Override save to validate video file before saving."""
        # Only validate if there's a new video file being uploaded
        if self.video_file and not self.pk:
            from cw.lib.security import VideoFileValidator
            from django.core.exceptions import ValidationError

            validator = VideoFileValidator()
            try:
                validator.validate(self.video_file)
            except ValidationError as e:
                # Re-raise with context about which model failed
                raise ValidationError(f"Video file validation failed: {e}")

        super().save(*args, **kwargs)


class VideoProcessingResult(models.Model):
    """Complete analysis results from video processing pipeline.

    Stores all extracted data: scenes, script, transcription, visual style,
    sentiment analysis, and audience insights generated from uploaded video.
    """

    # Scene data
    scenes = models.JSONField(
        default=list,
        help_text="""List of detected scenes with metadata:
        [{
            "scene_number": 1,
            "start_time": 0.0,
            "end_time": 3.5,
            "duration": 3.5,
            "visual_description": "...",
            "objects_detected": ["product", "person"],
            "colors": ["#FF5733", "#33FF57"],
            "lighting": "warm, golden hour",
            "camera_angle": "medium shot",
            "sentiment": "positive"
        }]
        """,
    )

    # Generated script (tvspot.schema.json format)
    script = models.JSONField(
        default=dict,
        help_text="""Structured script matching tvspot.schema.json:
        {
            "scenes": [
                {
                    "scene_number": 1,
                    "duration": 3.5,
                    "visual": "Description...",
                    "audio": {
                        "voiceover": "Text...",
                        "music": "Description...",
                        "sfx": "Sound effects..."
                    },
                    "action": "Camera movements...",
                    "products": ["Product names"],
                    "sentiment": "emotional tone"
                }
            ]
        }
        """,
    )

    # Audio transcription
    transcription = models.JSONField(
        default=dict,
        help_text="""Full audio transcription with timestamps:
        {
            "language": "en-US",
            "confidence": 0.95,
            "segments": [
                {
                    "start": 0.5,
                    "end": 3.2,
                    "text": "Transcribed text...",
                    "speaker": "narrator",
                    "confidence": 0.96
                }
            ]
        }
        """,
    )

    # Visual analysis
    visual_style = models.JSONField(
        default=dict,
        help_text="""Overall visual style analysis from keyframes:
        {
            "dominant_colors": ["#FF5733", "#3357FF", ...],
            "avg_brightness": 0.58,
            "avg_contrast": 0.45,
            "lighting_distribution": {"soft": 3, "harsh": 1, "dramatic": 1},
            "exposure_distribution": {"normal": 4, "overexposed": 1},
            "camera_work": {
                "avg_scene_duration": 4.5,
                "total_scenes": 12,
                "pacing": "fast",
                "scene_transitions": 11
            }
        }
        """,
    )

    # Object detection summary
    objects_summary = models.JSONField(
        default=dict,
        help_text="""Aggregated object detection from YOLO v8:
        {
            "total_objects": 15,
            "classes": {
                "person": {"count": 5, "avg_confidence": 0.92},
                "car": {"count": 2, "avg_confidence": 0.85},
                "bottle": {"count": 3, "avg_confidence": 0.88}
            },
            "most_common": ["person", "car", "bottle"]
        }
        """,
    )

    # Sentiment analysis
    sentiment_analysis = models.JSONField(
        default=dict,
        help_text="""Sentiment analysis from audio and visual data:
        {
            "overall_sentiment": "positive",
            "overall_score": 0.65,
            "confidence": 0.72,
            "text_sentiment": {
                "sentiment": "positive",
                "score": 0.75,
                "confidence": 0.68
            },
            "visual_sentiment": {
                "sentiment": "positive",
                "score": 0.6,
                "brightness_factor": 0.7,
                "object_factor": 0.5
            }
        }
        """,
    )

    # Scene categorization
    categories = models.JSONField(
        default=dict,
        help_text="""Scene categorization summary:
        {
            "total_scenes": 10,
            "category_counts": {
                "people": 6,
                "product": 4,
                "lifestyle": 3
            },
            "primary_categories": ["people", "product", "lifestyle"]
        }
        """,
    )

    # Audience insights
    audience_insights = models.JSONField(
        default=dict,
        help_text="""AI-generated audience targeting insights:
        {
            "primary_audience": {
                "demographics": {"age_range": "25-45", ...},
                "psychographics": {"values": [...], ...}
            },
            "secondary_audiences": [...],
            "market_potential": {
                "high_fit_markets": ["US", "UK", "DE"],
                "considerations": [...]
            }
        }
        """,
    )

    # Processing metadata
    processing_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Total processing time in seconds",
    )
    models_used = models.JSONField(
        default=dict,
        help_text="""Track which models/APIs were used:
        {
            "scene_detection": "PySceneDetect",
            "transcription": "Whisper Large v3",
            "object_detection": "YOLO v8x",
            "visual_style": "OpenCV + k-means",
            "sentiment": "keyword-based",
            "script_generation": "Basic (MVP)"
        }
        """,
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tvspots_videoprocessingresult"
        verbose_name = "Video Processing Result"
        verbose_name_plural = "Video Processing Results"

    def __str__(self):
        return f"Processing Result (created {self.created_at:%Y-%m-%d %H:%M})"


class KeyFrame(models.Model):
    """Representative frame from a detected scene.

    Stores extracted key frames with visual analysis metadata including
    object detection results and dominant colors.
    """

    result = models.ForeignKey(
        "VideoProcessingResult",
        on_delete=models.CASCADE,
        related_name="key_frames",
    )
    scene_number = models.IntegerField(help_text="Scene this frame represents")
    timestamp = models.FloatField(help_text="Time in seconds")
    image = models.ImageField(upload_to="keyframes/%Y/%m/")

    # Visual analysis for this specific frame
    detected_objects = models.JSONField(
        default=list,
        help_text="""Objects detected in this frame:
        [
            {"label": "person", "confidence": 0.95, "bbox": [x, y, w, h]},
            {"label": "product", "confidence": 0.88, "bbox": [x, y, w, h]}
        ]
        """,
    )
    colors = models.JSONField(
        default=list,
        help_text="Dominant colors as hex codes: ['#FF5733', '#33FF57']",
    )

    # Embeddings for similarity search (future use)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="CLIP or similar embedding vector for similarity search",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tvspots_keyframe"
        ordering = ["result", "scene_number", "timestamp"]
        unique_together = [["result", "scene_number"]]
        verbose_name = "Key Frame"
        verbose_name_plural = "Key Frames"

    def __str__(self):
        return f"KeyFrame Scene {self.scene_number} @ {self.timestamp}s"
