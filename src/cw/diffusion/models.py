"""
Django models for Generative Creative Lab diffusion image generation system.

Models are based on the presets.json structure and integrate with
the existing lib modules (models/*, loras/*, prompt_enhancer).
"""

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

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
        help_text="Base model architecture (determines LoRA compatibility)",
    )
    path = models.CharField(
        max_length=500,
        help_text="HuggingFace model ID (e.g., 'Qwen/Qwen-Image-2512') or local path",
    )
    pipeline = models.CharField(
        max_length=100, help_text="Pipeline class name (e.g., 'ZImagePipeline', 'FluxPipeline')"
    )

    # Settings (stored as JSON for flexibility)
    steps = models.IntegerField(
        default=28,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Default number of inference steps",
    )
    guidance_scale = models.FloatField(
        default=3.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Default guidance scale (CFG)",
    )
    default_width = models.IntegerField(
        default=1024,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Default image width in pixels",
    )
    default_height = models.IntegerField(
        default=1024,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Default image height in pixels",
    )
    max_pixels = models.IntegerField(
        default=1048576, help_text="Maximum total pixels (width * height)"
    )
    scheduler = models.CharField(
        max_length=100,
        blank=True,
        default="",
        choices=SCHEDULER_CHOICES,
        help_text="Default scheduler for this model",
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
        help_text="Data type for model weights",
    )
    supports_negative_prompt = models.BooleanField(
        default=False, help_text="Whether this model supports negative prompts"
    )
    force_default_guidance = models.BooleanField(
        default=False,
        help_text="Force model's default guidance_scale (Turbo models). Prevents LoRA/job overrides.",
    )
    max_sequence_length = models.IntegerField(
        blank=True, null=True, help_text="Maximum sequence length for text encoder"
    )
    token_window = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum tokens for prompt input (e.g. 77 for CLIP, 512 for T5)",
    )
    vram_usage = models.IntegerField(
        blank=True, null=True, help_text="Minimum VRAM required in MB (e.g. 8192 for 8GB)"
    )

    # Metadata
    is_active = models.BooleanField(default=True, help_text="Enable/disable this model")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diffusion Model"
        verbose_name_plural = "Diffusion Models"
        ordering = ["label"]

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
        help_text="Path to LoRA file (relative to base_model_path or HF model ID). Optional if AIR is provided.",
    )
    air = models.CharField(max_length=500, blank=True, help_text="AIR (AI Resource) URN identifier")

    # Compatibility
    base_architecture = models.CharField(
        max_length=20,
        choices=BASE_ARCHITECTURE_CHOICES,
        default="sdxl",
        help_text="Base model architecture this LoRA is trained for",
    )

    # Prompt and settings
    prompt_suffix = models.TextField(
        blank=True, help_text="Trigger words and style description to append to prompts"
    )
    negative_prompt_suffix = models.TextField(
        blank=True,
        help_text="Terms to append to negative prompts (only applied when model supports negative prompts)",
    )
    default_strength = models.FloatField(
        default=0.8,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="Default LoRA strength/weight",
    )
    guidance_scale = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Override guidance scale (CFG) when using this LoRA. Leave blank to use model/job default.",
    )
    clip_skip = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Number of CLIP layers to skip (1-12). Leave blank to use model default. Commonly 1 or 2 for anime/artistic styles.",
    )
    notes = models.TextField(
        blank=True, help_text="Internal notes about this LoRA (usage tips, characteristics, etc.)"
    )
    theme = models.CharField(
        max_length=100,
        blank=True,
        help_text="Theme or category for filtering (e.g., 'anime', 'photorealistic', 'fantasy')",
    )

    # Metadata
    is_active = models.BooleanField(default=True, help_text="Enable/disable this LoRA")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LoRA Model"
        verbose_name_plural = "LoRA Models"
        ordering = ["label"]

    def __str__(self):
        return self.label

    def get_settings_dict(self):
        """Return settings as a dictionary matching presets.json format."""
        settings = {"strength": self.default_strength}
        if self.guidance_scale is not None:
            settings["guidance_scale"] = self.guidance_scale
        if self.clip_skip is not None:
            settings["clip_skip"] = self.clip_skip
        return settings


CONTROL_TYPE_CHOICES = [
    ("canny", "Canny Edge"),
    ("lineart", "Line Art"),
    ("lineart_anime", "Line Art (Anime)"),
    ("depth", "Depth (MiDaS)"),
    ("softedge", "Soft Edge (HED)"),
    ("openpose", "OpenPose"),
]


class ControlNetModel(models.Model):
    """Represents a ControlNet conditioning model.

    ControlNet models provide structural guidance (edges, depth, poses)
    for image generation. Must be paired with a base diffusion model
    of the same architecture.
    """

    label = models.CharField(max_length=255, help_text="Display name for the ControlNet")
    slug = models.SlugField(max_length=100, unique=True, help_text="Unique identifier")
    path = models.CharField(
        max_length=500,
        help_text="HuggingFace model ID (e.g., 'diffusers/controlnet-canny-sdxl-1.0')",
    )
    control_type = models.CharField(
        max_length=20,
        choices=CONTROL_TYPE_CHOICES,
        help_text="Type of structural control this model provides",
    )
    base_architecture = models.CharField(
        max_length=20,
        choices=BASE_ARCHITECTURE_CHOICES,
        default="sdxl",
        help_text="Base model architecture (must match paired DiffusionModel)",
    )
    default_conditioning_scale = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="Default conditioning scale (0.5 for SDXL, 1.0 for SD1.5). "
        "Higher values follow the control image more strictly.",
    )
    default_guidance_end = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="When to stop applying ControlNet (fraction of total steps, 0.0-1.0). "
        "Lower values give the model more creative freedom in later steps.",
    )

    is_active = models.BooleanField(default=True, help_text="Enable/disable this ControlNet")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ControlNet Model"
        verbose_name_plural = "ControlNet Models"
        ordering = ["base_architecture", "control_type"]

    def __str__(self):
        return self.label


class Prompt(models.Model):
    """Stores prompts with enhancement tracking."""

    STYLE_CHOICES = [
        ("auto", "Auto-detect"),
        ("photography", "Photography"),
        ("artistic", "Artistic"),
        ("realistic", "Realistic"),
        ("cinematic", "Cinematic"),
        ("coloring-book", "Coloring Book"),
    ]

    ENHANCEMENT_METHOD_CHOICES = [
        ("none", "No Enhancement"),
        ("rule-based", "Rule-based"),
        ("huggingface", "HuggingFace Local Model"),
        ("llm", "LLM API"),
    ]

    # Source prompt
    source_prompt = models.TextField(help_text="Original user-provided prompt")

    # Enhanced versions
    enhanced_prompt = models.TextField(blank=True, help_text="AI-enhanced version of the prompt")
    negative_prompt = models.TextField(blank=True, help_text="Negative prompt (things to avoid)")

    # Enhancement settings
    enhancement_style = models.CharField(
        max_length=50, choices=STYLE_CHOICES, default="auto", help_text="Style used for enhancement"
    )
    enhancement_method = models.CharField(
        max_length=50,
        choices=ENHANCEMENT_METHOD_CHOICES,
        default="none",
        help_text="Method used to enhance the prompt",
    )
    creativity = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Creativity level for enhancement (0.0-1.0)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prompt"
        verbose_name_plural = "Prompts"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.source_prompt[:50]}..." if len(self.source_prompt) > 50 else self.source_prompt
        )


class DiffusionJob(models.Model):
    """Tracks diffusion image generation jobs.

    Jobs are processed by Django-RQ workers.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    # Job configuration
    diffusion_model = models.ForeignKey(
        DiffusionModel,
        on_delete=models.PROTECT,
        related_name="jobs",
        help_text="Model to use for generation",
    )
    lora_model = models.ForeignKey(
        LoraModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        help_text="Optional LoRA to apply",
    )
    prompt = models.ForeignKey(
        Prompt,
        on_delete=models.PROTECT,
        related_name="jobs",
        help_text="Prompt to use for generation",
    )
    identifier = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional identifier for file naming (e.g., 'hero-shot', 'product-v2')",
    )

    # Generation parameters (override model defaults if set)
    width = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Image width (uses model default if not set)",
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(256), MaxValueValidator(4096)],
        help_text="Image height (uses model default if not set)",
    )
    steps = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text="Number of steps (uses model default if not set)",
    )
    guidance_scale = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        help_text="Guidance scale (uses model default if not set)",
    )
    lora_strength = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="LoRA strength (uses LoRA default if not set)",
    )
    seed = models.BigIntegerField(
        null=True, blank=True, help_text="Random seed for reproducibility (random if not set)"
    )
    scheduler = models.CharField(
        max_length=100,
        blank=True,
        default="",
        choices=SCHEDULER_CHOICES,
        help_text="Override scheduler. Leave blank to use model default.",
    )
    num_images = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Number of images to generate",
    )

    # ControlNet parameters (optional — used for structure-guided generation)
    controlnet_model = models.ForeignKey(
        ControlNetModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        help_text="Optional ControlNet for structure-guided generation",
    )
    reference_image = models.ImageField(
        upload_to="diffusion/reference/%Y/%m/",
        null=True,
        blank=True,
        help_text="Source image for ControlNet conditioning (e.g., extracted keyframe)",
    )
    preprocessing_type = models.CharField(
        max_length=20,
        choices=CONTROL_TYPE_CHOICES,
        blank=True,
        default="",
        help_text="Preprocessing to apply to reference image. "
        "Leave blank to use ControlNet model's default control type.",
    )
    conditioning_scale = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text="ControlNet conditioning scale (uses ControlNet default if not set). "
        "Higher values follow the control image more strictly.",
    )
    control_guidance_end = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="When to stop applying ControlNet (fraction of steps). "
        "Uses ControlNet default if not set.",
    )

    # Job status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", help_text="Current job status"
    )
    rq_job_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Celery task ID for tracking (field name retained for compatibility)",
    )

    # Results
    result_images = ArrayField(
        models.CharField(max_length=500),
        blank=True,
        default=list,
        help_text="List of generated image paths",
    )
    generation_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Complete generation settings used (prompt, seed, parameters, etc.)",
    )
    error_message = models.TextField(blank=True, help_text="Error message if job failed")

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Diffusion Job"
        verbose_name_plural = "Diffusion Jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job #{self.pk} - {self.get_status_display()} ({self.diffusion_model.label})"

    def get_generation_params(self):
        """Return complete generation parameters, using model/LoRA defaults where needed."""
        params = {
            "model_slug": self.diffusion_model.slug,
            "prompt": self.prompt.enhanced_prompt or self.prompt.source_prompt,
            "width": self.width or self.diffusion_model.default_width,
            "height": self.height or self.diffusion_model.default_height,
            "steps": self.steps or self.diffusion_model.steps,
            "guidance_scale": self.guidance_scale or self.diffusion_model.guidance_scale,
            "seed": self.seed,
            "num_images": self.num_images,
        }

        # Scheduler: job override → model default → None (use pipeline default)
        scheduler = self.scheduler or self.diffusion_model.scheduler
        if scheduler:
            params["scheduler"] = scheduler

        if self.diffusion_model.supports_negative_prompt and self.prompt.negative_prompt:
            params["negative_prompt"] = self.prompt.negative_prompt

        if self.lora_model:
            params["lora_path"] = self.lora_model.path
            params["lora_strength"] = self.lora_strength or self.lora_model.default_strength

        # ControlNet parameters
        if self.controlnet_model:
            params["controlnet_path"] = self.controlnet_model.path
            params["controlnet_slug"] = self.controlnet_model.slug
            params["preprocessing_type"] = (
                self.preprocessing_type or self.controlnet_model.control_type
            )
            params["conditioning_scale"] = (
                self.conditioning_scale
                if self.conditioning_scale is not None
                else self.controlnet_model.default_conditioning_scale
            )
            params["guidance_end"] = (
                self.control_guidance_end
                if self.control_guidance_end is not None
                else self.controlnet_model.default_guidance_end
            )
            if self.reference_image:
                params["reference_image_path"] = self.reference_image.path

        return params
