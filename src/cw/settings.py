"""
Django settings for cw project.

Generated for Django 6.0.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

import os
from pathlib import Path

from django.templatetags.static import static

# Build paths inside the project like this: PROJECT_ROOT / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent  # Points to src/
PROJECT_ROOT = BASE_DIR.parent  # Points to project root (where manage.py lives)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-dev-key-change-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    "unfold",  # Must come before django.contrib.admin
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # Required for ArrayField
    "cw.core",  # Core models (LLMModel, PromptTemplate)
    "cw.audiences",
    "cw.diffusion",
    "cw.tvspots",
    "django_extensions",
    "django_celery_results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cw.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cw.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "cw"),
        "USER": os.getenv("POSTGRES_USER", "cw"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "cw_dev"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5435"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"

# Media files (user-uploaded content)
MEDIA_URL = "media/"
MEDIA_ROOT = PROJECT_ROOT / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django Unfold Admin Configuration
# https://unfoldadmin.com/docs/configuration/

UNFOLD = {
    "SITE_TITLE": "Generative Creative Lab",
    "SITE_HEADER": "Generative Creative Lab",
    "SITE_SUBHEADER": "Multi-Model Diffusion Pipeline",
    # THEME omitted to enable user theme switcher (light/dark toggle)
    "SITE_DROPDOWN": [],
    "STYLES": [
        lambda request: static("core/css/styles.css"),
    ],
    "SIDEBAR": {
        "navigation": [
            {
                "title": "Generative AI",
                "collapsible": True,
                "items": [
                    {
                        "title": "Prompts",
                        "icon": "edit_note",
                        "link": "/app/diffusion/prompt/",
                    },
                    {
                        "title": "Jobs",
                        "icon": "precision_manufacturing",
                        "link": "/app/diffusion/diffusionjob/",
                    },
                    {
                        "title": "Diffusion Models",
                        "icon": "neurology",
                        "link": "/app/diffusion/diffusionmodel/",
                    },
                    {
                        "title": "LoRAs",
                        "icon": "tune",
                        "link": "/app/diffusion/loramodel/",
                    },
                ],
            },
            {
                "title": "Campaign Management",
                "collapsible": True,
                "items": [
                    {
                        "title": "Campaigns",
                        "icon": "live_tv",
                        "link": "/app/tvspots/campaign/",
                    },
                    {
                        "title": "Video Ad Units",
                        "icon": "description",
                        "link": "/app/tvspots/videoadunit/",
                    },
                    {
                        "title": "Storyboards",
                        "icon": "dashboard",
                        "link": "/app/tvspots/storyboard/",
                    },
                ],
            },
            {
                "title": "Audience Segmentation",
                "collapsible": True,
                "items": [
                    {
                        "title": "Personas",
                        "icon": "person",
                        "link": "/app/audiences/persona/",
                    },
                    {
                        "title": "Segments",
                        "icon": "category",
                        "link": "/app/audiences/segment/",
                    },
                    {
                        "title": "Regions",
                        "icon": "public",
                        "link": "/app/audiences/region/",
                    },
                    {
                        "title": "Countries",
                        "icon": "flag",
                        "link": "/app/audiences/country/",
                    },
                    {
                        "title": "Languages",
                        "icon": "translate",
                        "link": "/app/audiences/language/",
                    },
                ],
            },
            {
                "title": "Core",
                "collapsible": True,
                "items": [
                    {
                        "title": "LLM Models",
                        "icon": "smart_toy",
                        "link": "/app/core/llmmodel/",
                    },
                    {
                        "title": "Prompt Templates",
                        "icon": "code",
                        "link": "/app/core/prompttemplate/",
                    },
                    {
                        "title": "Brands",
                        "icon": "branding_watermark",
                        "link": "/app/tvspots/brand/",
                    },
                    {
                        "title": "Pipeline Settings",
                        "icon": "tune",
                        "link": "/app/core/pipelinesettings/",
                    },
                ],
            },
            {
                "title": "Celery",
                "collapsible": True,
                "items": [
                    {
                        "title": "Task Results",
                        "icon": "task_alt",
                        "link": "/app/django_celery_results/taskresult/",
                    },
                    {
                        "title": "Group Results",
                        "icon": "workspaces",
                        "link": "/app/django_celery_results/groupresult/",
                    },
                ],
            },
            {
                "title": "Auth",
                "collapsible": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": "/app/auth/user/",
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": "/app/auth/group/",
                    },
                ],
            },
        ],
    },
}


# Model and LoRA base path (for diffusion models)
# This is where local model files and LoRAs are stored
MODEL_BASE_PATH = Path(os.getenv("MODEL_BASE_PATH", PROJECT_ROOT / "models"))
CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY", "")


# Video Upload Security Settings
# Maximum file size for video uploads (bytes)
VIDEO_MAX_UPLOAD_SIZE_BYTES = int(
    os.getenv("VIDEO_MAX_UPLOAD_SIZE_BYTES", 500 * 1024 * 1024)  # 500 MB default
)

# Allowed video file extensions
VIDEO_ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

# Allowed MIME types for video uploads
VIDEO_ALLOWED_MIME_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
]

# Enable MIME type content verification (uses libmagic)
VIDEO_VERIFY_MIME_CONTENT = True

# Enable file header validation (magic bytes check)
VIDEO_VALIDATE_HEADERS = True

# Enable filename sanitization
VIDEO_SANITIZE_FILENAMES = True

# Upload rate limiting (optional - future implementation)
VIDEO_UPLOAD_RATE_LIMIT_ENABLED = False
VIDEO_UPLOAD_RATE_LIMIT_PER_USER = 10  # uploads per hour
VIDEO_UPLOAD_RATE_LIMIT_PER_IP = 20  # uploads per hour

# Virus scanning (optional - future implementation)
VIDEO_VIRUS_SCAN_ENABLED = False
VIDEO_VIRUS_SCAN_ENDPOINT = ""  # ClamAV endpoint if enabled


# Logging Configuration
# Creates logs directory and configures Django and Celery logging

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "django_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "django.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "celery.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
        "tasks_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "tasks.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "django_file"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "cw.diffusion.tasks": {
            "handlers": ["console", "tasks_file"],
            "level": "INFO",
            "propagate": False,
        },
        "cw.lib.adaptation": {
            "handlers": ["console", "tasks_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cw.lib.models": {
            "handlers": ["console", "tasks_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cw.lib.prompt_enhancer": {
            "handlers": ["console", "tasks_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cw.lib.storyboard": {
            "handlers": ["console", "tasks_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cw.lib.civitai": {
            "handlers": ["console", "tasks_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "cw.lib.security": {
            "handlers": ["console", "tasks_file"],
            "level": "INFO",
            "propagate": False,
        },
        "cw.tvspots.tasks": {
            "handlers": ["console", "tasks_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


# Celery Configuration
# https://docs.celeryproject.org/en/stable/userguide/configuration.html

# Broker settings (using Valkey/Redis)
CELERY_BROKER_URL = (
    f'redis://{os.getenv("VALKEY_HOST", "localhost")}:{int(os.getenv("VALKEY_PORT", 6379))}/2'
)

# Result backend (stores task results in Django ORM)
CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_EXTENDED = True

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 minutes soft limit

# Worker pool settings
# Use 'solo' pool to avoid fork() issues with MPS on macOS
# This allows GPU (MPS/CUDA) usage in Celery workers
CELERY_WORKER_POOL = "solo"

# Serialization settings
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

# Task routing (queues)
CELERY_TASK_ROUTES = {
    "cw.diffusion.tasks.enhance_prompt_task": {"queue": "enhancement"},
    "cw.diffusion.tasks.generate_images_task": {"queue": "default"},
}

# Queue configuration
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "enhancement": {
        "exchange": "enhancement",
        "routing_key": "enhancement",
    },
}
