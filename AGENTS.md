# AGENTS.md

This file provides guidance for agentic coding assistants working in the Generative Creative Lab repository.

## Project Overview

Generative Creative Lab is a Django + Celery application for multi-model diffusion image generation. Uses Django Unfold for admin UI, PostgreSQL for storage, and Valkey/Redis as Celery broker. Supports Z-Image Turbo, Flux.1-dev, Flux.2 Klein, Qwen-Image-2512, SDXL Turbo, and other diffusion models.

## Build & Development Commands

### Package Management
```bash
uv sync                          # Install/sync dependencies
```

### Development Server
```bash
honcho start                     # Start all processes (Docker, Django, Celery workers)
honcho start docker django       # Start subset (without workers)
uv run manage.py runserver       # Django dev server only (:8000)
```

### Database Management
```bash
uv run manage.py migrate         # Run migrations
uv run manage.py import_presets  # Sync data/presets.json → database
uv run manage.py export_presets  # Export models/LoRAs from DB to JSON
uv run manage.py createsuperuser # Create admin user
```

### Individual Processes (from Procfile)
```bash
docker compose up                               # PostgreSQL 17 + Valkey + Grafana/Loki
uv run celery -A cw worker -Q default   # Image generation worker
uv run celery -A cw worker -Q enhancement  # Prompt enhancement worker
```

### Testing
```bash
# No comprehensive test suite currently exists
# Use Django TestCase for new tests:
uv run manage.py test                    # Run Django tests
uv run manage.py test tvspots.tests     # Run specific test module
```

### Code Quality
```bash
# Linting configured via .flake8 (line length: 100, max complexity: 10)
flake8 src/                             # Lint all source code
# No formatting tool configured (consider adding Black or ruff)
```

### Documentation
```bash
cd docs && make html                    # Build Sphinx documentation
cd docs && make clean                   # Clean build artifacts
```

## Code Style Guidelines

### Import Organization (Google-style with type hints)
```python
#!/usr/bin/env python3  # For executable modules

# Standard library imports first
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Third-party imports
import torch
from PIL import Image
from django.contrib.postgres.fields import ArrayField

# Local imports
from cw.lib.models.base import BaseModel
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `BaseModel`, `FluxModel`, `DiffusionJob`)
- **Functions/Methods**: `snake_case` (e.g., `load_pipeline`, `generate_images_task`)
- **Variables**: `snake_case` (e.g., `model_path`, `guidance_scale`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BASE_ARCHITECTURE_CHOICES`)
- **Private methods**: Prefix with underscore (e.g., `_create_pipeline`, `_build_prompts`)

### Type Hints
Use throughout with `typing` module. Return types for all public methods.

### Docstrings
Google/NumPy style with Napoleon extension. Include:
- Module purpose and overview
- Example usage blocks (`::`)
- Important notes and warnings
- Parameter and return type documentation

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Loading model: {model_slug}")    # Detailed info
logger.error(f"Failed to load: {status}")      # Errors
```

## Architecture Patterns

### Template Method Pattern (Models)
- `BaseModel` provides concrete template methods (`load_pipeline`, `generate`)
- Concrete models override abstract hooks (`_create_pipeline`)
- Mixins provide shared behaviors (`CompelPromptMixin`, `DebugLoggingMixin`)

### Configuration-Driven Development
- `data/presets.json` as single source of truth
- Database sync via management commands
- Environment variables for secrets (`.env`)

### Process Architecture
- Four concurrent processes: docker, django, worker, enhancement
- Celery `solo` pool for GPU compatibility (no forking)
- JSON logging with Grafana/Loki aggregation

## File Structure Conventions

### Django Apps (`src/cw/diffusion/`, `src/cw/tvspots/`)
- `models.py` - ORM models with comprehensive docstrings
- `admin.py` - Django Unfold admin configurations
- `tasks.py` - Celery tasks (use `bind=True` for self-reference)
- `management/commands/` - Custom Django management commands

### Library Modules (`src/cw/lib/`)
- `models/` - Diffusion model implementations
- `loras/` - LoRA management utilities
- `config.py` - Configuration loading (`PresetsConfig`)
- `prompt_enhancer.py` - Multiple enhancement strategies
- `civitai.py` - External API integrations

## Error Handling Patterns

### Exception Handling
```python
try:
    self.preload_model(model_config)
    print(f"✅ {model_label} loaded successfully!")
except Exception as e:
    print(f"❌ Error loading {model_label}:")
    # User-friendly error messages, detailed logging
```

### Celery Tasks
- Use `bind=True` for task self-reference
- Return dictionaries with status information
- Log at appropriate levels for debugging
- Handle GPU memory errors gracefully

## Testing Guidelines

### Framework
- Use Django `TestCase` for new tests
- Test database operations with `django.test.TransactionTestCase`
- Mock external APIs (CivitAI, HuggingFace) in tests

### Test Structure
```python
from django.test import TestCase

class DiffusionModelTest(TestCase):
    def setUp(self):
        # Test setup
    
    def test_model_creation(self):
        # Test implementation
```

## Import Path Resolution

### Local Models/LoRAs
- Path ends with `.safetensors` → resolved as `{MODEL_BASE_PATH}/{path}`
- Loaded via `from_single_file()`

### HuggingFace Models
- Path starts with `Huggingface:` → prefix stripped
- Loaded via `from_pretrained()`

## Adding New Models

### Simple Models (10-20 lines)
1. Create `src/cw/lib/models/newmodel.py` inheriting from `BaseModel`
2. Override `_create_pipeline()` to return pipeline instance
3. Add to `src/cw/lib/models/__init__.py` exports and `ModelFactory.create_model()`
4. Add config to `data/presets.json` with appropriate flags
5. Run `uv run manage.py import_presets` to sync to database

### Models with Special Requirements
- **Long prompts + weighting**: Inherit from `CompelPromptMixin` + `BaseModel`
- **Debug logging**: Inherit from `DebugLoggingMixin` + `BaseModel`
- **Custom behavior**: Override hooks like `_build_prompts()`, `_build_pipeline_kwargs()`

## Environment Configuration

### Required Environment Variables
- `POSTGRES_*` - Database connection
- `VALKEY_*` - Celery broker
- `DJANGO_SECRET_KEY` - Django secret

### Optional Variables
- `ANTHROPIC_API_KEY` - LLM prompt enhancement
- `CIVITAI_API_KEY` - Auto-download LoRAs
- `MODEL_BASE_PATH` - Local model directory

## GPU & Performance Considerations

- Apple Silicon: MPS backend with `enable_sequential_cpu_offload()`
- One model loaded at a time (module-level `_model_cache`)
- `torch.mps.empty_cache()` called after each generation
- Use `torch.bfloat16` precision for all models
- Celery `solo` pool (single-threaded) for GPU compatibility