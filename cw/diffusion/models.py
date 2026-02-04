"""
Django models for Creative Workflow diffusion image generation system.

Models are based on the presets.json structure and integrate with
the existing lib modules (models/*, loras/*, prompt_enhancer).
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
import json


BASE_ARCHITECTURE_CHOICES = [
    ("sdxl", "SDXL"),
    ("sd15", "SD 1.5"),
    ("flux1", "Flux.1"),
    ("qwen", "Qwen"),
    ("zimage", "Z-Image (Lumina/S3-DiT)"),
]

SCHEDULER_CHOICES = [
    ("", "— Use pipeline default —"),
    # Euler family
    ("EulerDiscreteScheduler", "Euler"),
    ("EulerAncestralDiscreteScheduler", "Euler Ancestral"),
    # DPM family
    ("DPMSolverMultistepScheduler", "DPM++ 2M"),
    ("DPMSolverSinglestepScheduler", "DPM++ SDE"),
    ("KDPM2DiscreteScheduler", "DPM2"),
    ("KDPM2AncestralDiscreteScheduler", "DPM2 Ancestral"),
    # Flow matching (Flux, etc.)
    ("FlowMatchEulerDiscreteScheduler", "Flow Match Euler"),
    # Other popular schedulers
    ("DDIMScheduler", "DDIM"),
    ("DDPMScheduler", "DDPM"),
    ("PNDMScheduler", "PNDM"),
    ("HeunDiscreteScheduler", "Heun"),
    ("LMSDiscreteScheduler", "LMS"),
    ("UniPCMultistepScheduler", "UniPC"),
    ("LCMScheduler", "LCM"),
]


class DiffusionModel(models.Model):
    """Represents a diffusion model for image generation.

    Corresponds to models in presets.json.
    """

    # Basic info
    label = models.CharField(max_length=255, help_text="Display name for the model")
    slug = models.SlugField(max_length=100, unique=True, help_text="Unique identifier")
    base_architecture = models.CharField(
        max_length=20,
        choices=BASE_ARCHITECTURE_CHOICES,
        default="sdxl",
        help_text="Base model architecture (determines LoRA compatibility)"
    )
    path = models.CharField(
        max_length=500,
        help_text="HuggingFace model ID (e.g., 'Qwen/Qwen-Image-2512') or local path"
    )
    pipeline = models.CharField(
        max_length=100,
        help_text="Pipeline class name (e.g., 'ZImagePipeline', 'FluxPipeline')"
    )

    # Settings (stored as JSON for flexibility)
    steps = models.IntegerField(
        default=28,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Default number of inference steps"
    )
    guidance_scale = models.FloatField(
        default=3.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Default guidance scale (CFG)"
    )
    default_width = models.IntegerField(
        default=1024,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Default image width in pixels"
    )
    default_height = models.IntegerField(
        default=1024,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Default image height in pixels"
    )
    max_pixels = models.IntegerField(
        default=1048576,
        help_text="Maximum total pixels (width * height)"
    )
    scheduler = models.CharField(
        max_length=100,
        blank=True,
        default="",
        choices=SCHEDULER_CHOICES,
        help_text="Default scheduler for this model"
    )
    dtype = models.CharField(
        max_length=50,
        default="bfloat16",
        choices=[
            ("bfloat16", "BFloat16"),
            ("float16", "Float16"),
            ("float32", "Float32"),
            ("float8_e4m3fn", "Float8 (E4M3)"),
        ],
        help_text="Data type for model weights"
    )
    supports_negative_prompt = models.BooleanField(
        default=False,
        help_text="Whether this model supports negative prompts"
    )
    force_default_guidance = models.BooleanField(
        default=False,
        help_text="Force model's default guidance_scale (Turbo models). Prevents LoRA/job overrides."
    )
    max_sequence_length = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum sequence length for text encoder"
    )
    token_window = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum tokens for prompt input (e.g. 77 for CLIP, 512 for T5)"
    )
    vram_usage = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum VRAM required in MB (e.g. 8192 for 8GB)"
    )

    # Metadata
    is_active = models.BooleanField(default=True, help_text="Enable/disable this model")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diffusion Model"
        verbose_name_plural = "Diffusion Models"
        ordering = ['label']

    def __str__(self):
        return self.label

    def get_settings_dict(self):
        """Return settings as a dictionary matching presets.json format."""
        return {
            "steps": self.steps,
            "guidance_scale": self.guidance_scale,
            "force_default_guidance": self.force_default_guidance,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "max_pixels": self.max_pixels,
            "scheduler": self.scheduler,
            "dtype": self.dtype,
            "supports_negative_prompt": self.supports_negative_prompt,
            "max_sequence_length": self.max_sequence_length,
        }


class LoraModel(models.Model):
    """Represents a LoRA (Low-Rank Adaptation) model.

    Corresponds to loras in presets.json.
    """

    # Basic info
    label = models.CharField(max_length=255, help_text="Display name for the LoRA")
    path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to LoRA file (relative to base_model_path or HF model ID). Optional if AIR is provided."
    )
    air = models.CharField(
        max_length=500,
        blank=True,
        help_text="AIR (AI Resource) URN identifier"
    )

    # Compatibility
    base_architecture = models.CharField(
        max_length=20,
        choices=BASE_ARCHITECTURE_CHOICES,
        default="sdxl",
        help_text="Base model architecture this LoRA is trained for"
    )

    # Prompt and settings
    prompt_suffix = models.TextField(
        blank=True,
        help_text="Trigger words and style description to append to prompts"
    )
    negative_prompt_suffix = models.TextField(
        blank=True,
        help_text="Terms to append to negative prompts (only applied when model supports negative prompts)"
    )
    default_strength = models.FloatField(
        default=0.8,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="Default LoRA strength/weight"
    )
    guidance_scale = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Override guidance scale (CFG) when using this LoRA. Leave blank to use model/job default."
    )
    clip_skip = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Number of CLIP layers to skip (1-12). Leave blank to use model default. Commonly 1 or 2 for anime/artistic styles."
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this LoRA (usage tips, characteristics, etc.)"
    )
    theme = models.CharField(
        max_length=100,
        blank=True,
        help_text="Theme or category for filtering (e.g., 'anime', 'photorealistic', 'fantasy')"
    )

    # Metadata
    is_active = models.BooleanField(default=True, help_text="Enable/disable this LoRA")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LoRA Model"
        verbose_name_plural = "LoRA Models"
        ordering = ['label']

    def __str__(self):
        return self.label

    def get_settings_dict(self):
        """Return settings as a dictionary matching presets.json format."""
        settings = {
            "strength": self.default_strength
        }
        if self.guidance_scale is not None:
            settings["guidance_scale"] = self.guidance_scale
        if self.clip_skip is not None:
            settings["clip_skip"] = self.clip_skip
        return settings


class Prompt(models.Model):
    """Stores prompts with enhancement tracking."""

    STYLE_CHOICES = [
        ('auto', 'Auto-detect'),
        ('photography', 'Photography'),
        ('artistic', 'Artistic'),
        ('realistic', 'Realistic'),
        ('cinematic', 'Cinematic'),
        ('coloring-book', 'Coloring Book'),
    ]

    ENHANCEMENT_METHOD_CHOICES = [
        ('none', 'No Enhancement'),
        ('rule-based', 'Rule-based'),
        ('huggingface', 'HuggingFace Local Model'),
        ('llm', 'LLM API'),
    ]

    # Source prompt
    source_prompt = models.TextField(help_text="Original user-provided prompt")

    # Enhanced versions
    enhanced_prompt = models.TextField(
        blank=True,
        help_text="AI-enhanced version of the prompt"
    )
    negative_prompt = models.TextField(
        blank=True,
        help_text="Negative prompt (things to avoid)"
    )

    # Enhancement settings
    enhancement_style = models.CharField(
        max_length=50,
        choices=STYLE_CHOICES,
        default='auto',
        help_text="Style used for enhancement"
    )
    enhancement_method = models.CharField(
        max_length=50,
        choices=ENHANCEMENT_METHOD_CHOICES,
        default='none',
        help_text="Method used to enhance the prompt"
    )
    creativity = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Creativity level for enhancement (0.0-1.0)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prompt"
        verbose_name_plural = "Prompts"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.source_prompt[:50]}..." if len(self.source_prompt) > 50 else self.source_prompt


class DiffusionJob(models.Model):
    """Tracks diffusion image generation jobs.

    Jobs are processed by Django-RQ workers.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Job configuration
    diffusion_model = models.ForeignKey(
        DiffusionModel,
        on_delete=models.PROTECT,
        related_name='jobs',
        help_text="Model to use for generation"
    )
    lora_model = models.ForeignKey(
        LoraModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='jobs',
        help_text="Optional LoRA to apply"
    )
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.PROTECT,
        related_name='jobs',
        help_text="Prompt to use for generation"
    )
    identifier = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional identifier for file naming (e.g., 'hero-shot', 'product-v2')"
    )

    # Generation parameters (override model defaults if set)
    width = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Image width (uses model default if not set)"
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Image height (uses model default if not set)"
    )
    steps = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Number of steps (uses model default if not set)"
    )
    guidance_scale = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Guidance scale (uses model default if not set)"
    )
    lora_strength = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="LoRA strength (uses LoRA default if not set)"
    )
    seed = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Random seed for reproducibility (random if not set)"
    )
    scheduler = models.CharField(
        max_length=100,
        blank=True,
        default="",
        choices=SCHEDULER_CHOICES,
        help_text="Override scheduler. Leave blank to use model default."
    )
    num_images = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Number of images to generate"
    )

    # Job status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current job status"
    )
    rq_job_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for tracking (field name retained for compatibility)"
    )

    # Results
    result_images = ArrayField(
        models.CharField(max_length=500),
        blank=True,
        default=list,
        help_text="List of generated image paths"
    )
    generation_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Complete generation settings used (prompt, seed, parameters, etc.)"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if job failed"
    )

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Diffusion Job"
        verbose_name_plural = "Diffusion Jobs"
        ordering = ['-created_at']

    def __str__(self):
        return f"Job #{self.pk} - {self.get_status_display()} ({self.diffusion_model.label})"

    def get_generation_params(self):
        """Return complete generation parameters, using model/LoRA defaults where needed."""
        params = {
            'model_slug': self.diffusion_model.slug,
            'prompt': self.prompt.enhanced_prompt or self.prompt.source_prompt,
            'width': self.width or self.diffusion_model.default_width,
            'height': self.height or self.diffusion_model.default_height,
            'steps': self.steps or self.diffusion_model.steps,
            'guidance_scale': self.guidance_scale or self.diffusion_model.guidance_scale,
            'seed': self.seed,
            'num_images': self.num_images,
        }

        # Scheduler: job override → model default → None (use pipeline default)
        scheduler = self.scheduler or self.diffusion_model.scheduler
        if scheduler:
            params['scheduler'] = scheduler

        if self.diffusion_model.supports_negative_prompt and self.prompt.negative_prompt:
            params['negative_prompt'] = self.prompt.negative_prompt

        if self.lora_model:
            params['lora_path'] = self.lora_model.path
            params['lora_strength'] = self.lora_strength or self.lora_model.default_strength

        return params


# =============================================================================
# TV Spot Adaptation Models
# =============================================================================


class AdaptationMarket(models.Model):
    """Target market for TV spot adaptations.

    Contains cultural and regulatory rules for the LLM to follow when
    creating market-specific adaptations.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Market name (e.g., 'US Hispanic', 'Japanese')."
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code (e.g., 'us-hispanic', 'jp')."
    )
    rules = models.TextField(
        help_text="Markdown-formatted cultural/regulatory rules for adaptation."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Adaptation Market"
        verbose_name_plural = "Adaptation Markets"

    def __str__(self):
        return self.name


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
        max_length=100,
        unique=True,
        help_text="Internal project ID (e.g., 'ACME-2024-001')."
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "TV Spot"
        verbose_name_plural = "TV Spots"

    def __str__(self):
        return f"{self.client_name} - {self.script_title}"

    @property
    def origin_version(self):
        """Return the origin version for this spot."""
        return self.versions.filter(version_type='origin').first()


class TvSpotVersion(models.Model):
    """A version of a TV spot - either origin or market adaptation.

    Each version has its own script rows. The origin version is created
    during import, and adaptation versions are created via LLM.
    """

    VERSION_TYPE_CHOICES = [
        ('origin', 'Origin'),
        ('adaptation', 'Adaptation'),
    ]

    tv_spot = models.ForeignKey(
        TvSpot,
        on_delete=models.CASCADE,
        related_name='versions',
    )
    version_type = models.CharField(
        max_length=20,
        choices=VERSION_TYPE_CHOICES,
        default='origin',
    )
    market = models.ForeignKey(
        AdaptationMarket,
        on_delete=models.PROTECT,
        related_name='versions',
        null=True,
        blank=True,
        help_text="Target market for adaptation. Null for origin versions."
    )
    code = models.CharField(
        max_length=50,
        help_text="Internal code (e.g., 'ORIGIN', 'US-HISP', 'JP')."
    )
    name = models.CharField(
        max_length=255,
        help_text="Human label (e.g., 'US Hispanic Adaptation')."
    )
    language = models.CharField(
        max_length=50,
        help_text="Primary language (e.g., 'en-US', 'es-MX', 'ja')."
    )
    visual_style_prompt = models.TextField(
        blank=True,
        help_text="Common prompt prefix for storyboard generation consistency."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tv_spot', 'code')
        ordering = ['tv_spot', 'version_type', 'code']

    def __str__(self):
        return f"{self.tv_spot.script_title} - {self.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.version_type == 'adaptation' and not self.market:
            raise ValidationError("Adaptation versions require a target market.")
        if self.version_type == 'origin' and self.market:
            raise ValidationError("Origin versions should not have a target market.")


class TvSpotScriptRow(models.Model):
    """A single row in the two-column AV script.

    Keeps visuals (left) and audio (right) aligned with timing metadata.
    """

    tv_spot_version = models.ForeignKey(
        TvSpotVersion,
        on_delete=models.CASCADE,
        related_name='script_rows',
    )
    order_index = models.PositiveIntegerField(
        help_text="Row order in script (0-indexed)."
    )
    shot_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Shot identifier (e.g., '01', '1A', 'MONT-01')."
    )
    timecode_start = models.CharField(
        max_length=12,
        blank=True,
        help_text="Start timecode (e.g., '00:00:05:00' or '5.0')."
    )
    duration_seconds = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Row duration in seconds (e.g., 2.50)."
    )
    visual_text = models.TextField(
        help_text="Left column: visuals, shots, graphics, supers, VFX, locations."
    )
    audio_text = models.TextField(
        help_text="Right column: VO, dialogue, SFX, music cues, taglines."
    )

    class Meta:
        ordering = ['tv_spot_version', 'order_index']
        unique_together = ('tv_spot_version', 'order_index')

    def __str__(self):
        shot = self.shot_number or f"Row {self.order_index}"
        return f"{self.tv_spot_version.code} - {shot}"


class StoryboardJob(models.Model):
    """A storyboard generation job for a TvSpotVersion.

    One StoryboardJob creates one DiffusionJob per script row (times images_per_row).
    Multiple StoryboardJobs can exist per version (different configs).
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    tv_spot_version = models.ForeignKey(
        TvSpotVersion,
        on_delete=models.CASCADE,
        related_name='storyboard_jobs',
    )
    diffusion_model = models.ForeignKey(
        DiffusionModel,
        on_delete=models.PROTECT,
        related_name='storyboard_jobs',
    )
    lora_model = models.ForeignKey(
        LoraModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='storyboard_jobs',
    )
    images_per_row = models.PositiveIntegerField(
        default=1,
        help_text="Number of images to generate per script row."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
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
        return self.images.filter(diffusion_job__status='completed').count()

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
        related_name='images',
    )
    script_row = models.ForeignKey(
        TvSpotScriptRow,
        on_delete=models.CASCADE,
        related_name='storyboard_images',
    )
    diffusion_job = models.ForeignKey(
        DiffusionJob,
        on_delete=models.CASCADE,
        related_name='storyboard_images',
    )
    image_index = models.PositiveIntegerField(
        default=0,
        help_text="Image sequence within the row (for multiple images per row)."
    )

    class Meta:
        ordering = ['script_row__order_index', 'image_index']
        unique_together = ('storyboard_job', 'script_row', 'image_index')

    def __str__(self):
        return f"{self.script_row} - Image {self.image_index + 1}"
