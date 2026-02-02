"""
Django settings for queerchaos project.

Generated for Django 6.0.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dev-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'unfold',  # Must come before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',  # Required for ArrayField
    'queerchaos.diffusion',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'queerchaos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'queerchaos.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'queerchaos'),
        'USER': os.getenv('POSTGRES_USER', 'queerchaos'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'queerchaos_dev'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5435'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user-uploaded content)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Model and LoRA base path (for diffusion models)
# This is where local model files and LoRAs are stored
MODEL_BASE_PATH = Path(os.getenv('MODEL_BASE_PATH', BASE_DIR / 'models'))


# Celery Configuration
# https://docs.celeryproject.org/en/stable/userguide/configuration.html

# Broker settings (using Valkey/Redis)
CELERY_BROKER_URL = f'redis://{os.getenv("VALKEY_HOST", "localhost")}:{int(os.getenv("VALKEY_PORT", 6379))}/2'

# Result backend (stores task results)
CELERY_RESULT_BACKEND = f'redis://{os.getenv("VALKEY_HOST", "localhost")}:{int(os.getenv("VALKEY_PORT", 6379))}/3'

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55 minutes soft limit

# Worker pool settings
# Use 'solo' pool to avoid fork() issues with MPS on macOS
# This allows GPU (MPS/CUDA) usage in Celery workers
CELERY_WORKER_POOL = 'solo'

# Serialization settings
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE

# Task routing (queues)
CELERY_TASK_ROUTES = {
    'queerchaos.diffusion.tasks.enhance_prompt_task': {'queue': 'enhancement'},
    'queerchaos.diffusion.tasks.generate_images_task': {'queue': 'default'},
}

# Queue configuration
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'enhancement': {
        'exchange': 'enhancement',
        'routing_key': 'enhancement',
    },
}

