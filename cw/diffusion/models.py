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
        null=True,
        help_text="Scheduler class name (e.g., 'FlowMatchEulerDiscreteScheduler')"
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
        return {
            "strength": self.default_strength
        }


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

        if self.diffusion_model.supports_negative_prompt and self.prompt.negative_prompt:
            params['negative_prompt'] = self.prompt.negative_prompt

        if self.lora_model:
            params['lora_path'] = self.lora_model.path
            params['lora_strength'] = self.lora_strength or self.lora_model.default_strength

        return params
