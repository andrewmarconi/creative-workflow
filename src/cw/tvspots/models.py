from django.db import models


class AdaptationMarket(models.Model):
    """Target market for TV spot adaptations.

    Contains cultural and regulatory rules for the LLM to follow when
    creating market-specific adaptations.

    The rules field stores structured JSON with headings and points::

        [
            {
                "heading": "Language segmentation",
                "points": [
                    "Belgium requires two distinct versions...",
                    "Luxembourg prefers French and German..."
                ]
            },
            {
                "heading": "Tone and register",
                "points": [
                    "Belgians are more reserved, formal, and indirect..."
                ]
            }
        ]

    Use :meth:`rules_as_markdown` to render as markdown for display.
    """

    name = models.CharField(
        max_length=100, unique=True, help_text="Market name (e.g., 'US Hispanic', 'Japanese')."
    )
    code = models.CharField(
        max_length=20, unique=True, help_text="Short code (e.g., 'us-hispanic', 'jp')."
    )
    rules = models.JSONField(
        default=list,
        help_text="Structured rules: list of {heading, points[]} objects for adaptation guidance.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "diffusion_adaptationmarket"
        ordering = ["name"]
        verbose_name = "Adaptation Market"
        verbose_name_plural = "Adaptation Markets"

    def __str__(self):
        return self.name

    def rules_as_markdown(self) -> str:
        """Render structured rules as markdown for display or LLM consumption.

        Returns:
            Markdown string with ### headings and - bullet points.

        Example output::

            ### Language segmentation
            - Belgium requires two distinct versions...
            - Luxembourg prefers French and German...

            ### Tone and register
            - Belgians are more reserved, formal, and indirect...
        """
        if not self.rules:
            return ""

        sections = []
        for section in self.rules:
            heading = section.get("heading", "")
            points = section.get("points", [])

            if heading:
                lines = [f"### {heading}"]
                for point in points:
                    lines.append(f"- {point}")
                sections.append("\n".join(lines))

        return "\n\n".join(sections)


class TvSpot(models.Model):
    """Project-level TV spot metadata.

    Represents a campaign spot before market adaptations.
    Created via JSON import (management command or admin action).
    """

    client_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=255, blank=True)
    script_title = models.CharField(max_length=255)
    total_runtime_seconds = models.PositiveIntegerField(
        help_text="Total runtime in seconds (typically 15, 30, 60, 90)."
    )
    job_id = models.CharField(
        max_length=100, unique=True, help_text="Internal project ID (e.g., 'ACME-2024-001')."
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "diffusion_tvspot"
        ordering = ["-created_at"]
        verbose_name = "TV Spot"
        verbose_name_plural = "TV Spots"

    def __str__(self):
        return f"{self.client_name} - {self.script_title}"

    @property
    def origin_version(self):
        """Return the origin version for this spot."""
        return self.versions.filter(version_type="origin").first()


class TvSpotVersion(models.Model):
    """A version of a TV spot - either origin or market adaptation.

    Each version has its own script rows. The origin version is created
    during import, and adaptation versions are created via LLM.
    """

    VERSION_TYPE_CHOICES = [
        ("origin", "Origin"),
        ("adaptation", "Adaptation"),
    ]

    tv_spot = models.ForeignKey(
        TvSpot,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_type = models.CharField(
        max_length=20,
        choices=VERSION_TYPE_CHOICES,
        default="origin",
    )
    market = models.ForeignKey(
        AdaptationMarket,
        on_delete=models.PROTECT,
        related_name="versions",
        null=True,
        blank=True,
        help_text="Target market for adaptation. Null for origin versions.",
    )
    code = models.CharField(
        max_length=50, help_text="Internal code (e.g., 'ORIGIN', 'US-HISP', 'JP')."
    )
    name = models.CharField(
        max_length=255, help_text="Human label (e.g., 'US Hispanic Adaptation')."
    )
    language = models.CharField(
        max_length=50, help_text="Primary language (e.g., 'en-US', 'es-MX', 'ja')."
    )
    visual_style_prompt = models.TextField(
        blank=True, help_text="Common prompt prefix for storyboard generation consistency."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "diffusion_tvspotversion"
        unique_together = ("tv_spot", "code")
        ordering = ["tv_spot", "version_type", "code"]

    def __str__(self):
        return f"{self.tv_spot.script_title} - {self.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.version_type == "adaptation" and not self.market:
            raise ValidationError("Adaptation versions require a target market.")
        if self.version_type == "origin" and self.market:
            raise ValidationError("Origin versions should not have a target market.")


class TvSpotScriptRow(models.Model):
    """A single row in the two-column AV script.

    Keeps visuals (left) and audio (right) aligned with timing metadata.
    """

    tv_spot_version = models.ForeignKey(
        TvSpotVersion,
        on_delete=models.CASCADE,
        related_name="script_rows",
    )
    order_index = models.PositiveIntegerField(help_text="Row order in script (0-indexed).")
    shot_number = models.CharField(
        max_length=20, blank=True, help_text="Shot identifier (e.g., '01', '1A', 'MONT-01')."
    )
    timecode_start = models.CharField(
        max_length=12, blank=True, help_text="Start timecode (e.g., '00:00:05:00' or '5.0')."
    )
    duration_seconds = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Row duration in seconds (e.g., 2.50).",
    )
    visual_text = models.TextField(
        help_text="Left column: visuals, shots, graphics, supers, VFX, locations."
    )
    audio_text = models.TextField(
        help_text="Right column: VO, dialogue, SFX, music cues, taglines."
    )

    class Meta:
        db_table = "diffusion_tvspotscriptrow"
        ordering = ["tv_spot_version", "order_index"]
        unique_together = ("tv_spot_version", "order_index")

    def __str__(self):
        shot = self.shot_number or f"Row {self.order_index}"
        return f"{self.tv_spot_version.code} - {shot}"


class StoryboardJob(models.Model):
    """A storyboard generation job for a TvSpotVersion.

    One StoryboardJob creates one DiffusionJob per script row (times images_per_row).
    Multiple StoryboardJobs can exist per version (different configs).
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    tv_spot_version = models.ForeignKey(
        TvSpotVersion,
        on_delete=models.CASCADE,
        related_name="storyboard_jobs",
    )
    # Cross-app reference to diffusion.DiffusionModel
    diffusion_model = models.ForeignKey(
        "diffusion.DiffusionModel",
        on_delete=models.PROTECT,
        related_name="storyboard_jobs",
    )
    # Cross-app reference to diffusion.LoraModel
    lora_model = models.ForeignKey(
        "diffusion.LoraModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storyboard_jobs",
    )
    images_per_row = models.PositiveIntegerField(
        default=1, help_text="Number of images to generate per script row."
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
        db_table = "diffusion_storyboardjob"
        ordering = ["-created_at"]
        verbose_name = "Storyboard Job"
        verbose_name_plural = "Storyboard Jobs"

    def __str__(self):
        return f"Storyboard for {self.tv_spot_version.code} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def total_jobs(self):
        """Total DiffusionJobs in this storyboard."""
        return self.images.count()

    @property
    def completed_jobs(self):
        """Completed DiffusionJobs in this storyboard."""
        return self.images.filter(diffusion_job__status="completed").count()

    @property
    def progress_percent(self):
        """Completion percentage."""
        total = self.total_jobs
        if total == 0:
            return 0
        return int((self.completed_jobs / total) * 100)


class StoryboardImage(models.Model):
    """Links a DiffusionJob to its StoryboardJob and source script row.

    Allows multiple images per row and multiple storyboard runs per version.
    """

    storyboard_job = models.ForeignKey(
        StoryboardJob,
        on_delete=models.CASCADE,
        related_name="images",
    )
    script_row = models.ForeignKey(
        TvSpotScriptRow,
        on_delete=models.CASCADE,
        related_name="storyboard_images",
    )
    # Cross-app reference to diffusion.DiffusionJob
    diffusion_job = models.ForeignKey(
        "diffusion.DiffusionJob",
        on_delete=models.CASCADE,
        related_name="storyboard_images",
    )
    image_index = models.PositiveIntegerField(
        default=0, help_text="Image sequence within the row (for multiple images per row)."
    )

    class Meta:
        db_table = "diffusion_storyboardimage"
        ordering = ["script_row__order_index", "image_index"]
        unique_together = ("storyboard_job", "script_row", "image_index")

    def __str__(self):
        return f"{self.script_row} - Image {self.image_index + 1}"
