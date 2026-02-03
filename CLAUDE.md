# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Creative Workflow is a Django + Celery application for multi-model diffusion image generation. It uses Django Unfold for the admin UI, PostgreSQL for storage, and Valkey/Redis as the Celery broker. Models supported: Z-Image Turbo, Flux.1-dev, Qwen-Image-2512, SDXL Turbo.

## Commands

### Setup & Run
```bash
uv sync                          # Install/sync dependencies
honcho start                     # Start all processes (Docker, Django, Celery workers)
```

### Individual Processes (from Procfile)
```bash
docker compose up                               # PostgreSQL 17 + Valkey
uv run manage.py runserver                      # Django dev server on :8000
uv run celery -A cw worker -Q default   # Image generation worker
uv run celery -A cw worker -Q enhancement  # Prompt enhancement worker
```

### Database & Django
```bash
uv run manage.py migrate                        # Run migrations
uv run manage.py import_presets                 # Sync data/presets.json → database
uv run manage.py export_presets                 # Export models/LoRAs from database to JSON
uv run manage.py import_prompts                 # Bulk import prompts
uv run manage.py export_prompts                 # Export prompts to file
uv run manage.py preload_models                 # Pre-download models to HF cache
uv run manage.py createsuperuser                # Create admin user
```

### Testing
```bash
uv run python test_admin.py                     # Run admin tests
```

### Observability & Logging
```bash
# View logs (JSON format)
tail -f logs/tasks.log                          # Task execution logs
tail -f logs/celery.log                         # Celery worker logs
tail -f logs/django.log                         # Django server logs

# Parse JSON logs with jq
cat logs/tasks.log | jq 'select(.levelname == "ERROR")'

# Start Jaeger (tracing UI)
# 1. Set OTEL_ENABLED=true in .env
# 2. Restart honcho (traces sent to Jaeger)
# 3. Access Jaeger UI at http://localhost:16686
```

## Architecture

### Process Model
Four processes run concurrently (defined in `Procfile`, launched via `honcho start`):
1. **docker** — PostgreSQL 17 (port 5435) + Valkey (port 6379) + Jaeger (optional tracing)
2. **django** — Django dev server (port 8000)
3. **worker** — Celery worker on `default` queue (image generation, GPU-intensive)
4. **enhancement** — Celery worker on `enhancement` queue (prompt enhancement via local LLM)

Celery uses `solo` pool (single-threaded) because MPS/CUDA contexts are not fork-safe.

**Jaeger Tracing** (via `docker-compose.yml`, optional):
- **Jaeger** (ports 4317/4318, UI: 16686) — All-in-one tracing backend with OTLP support

Enable by setting `OTEL_ENABLED=true` in `.env`. Access UI at http://localhost:16686.

### Model Architecture (Refactored 2026-02)

**Template Method Pattern** - Eliminates 70%+ code duplication:

**BaseModel** (`lib/models/base.py`) - Abstract base with concrete template methods:
- `load_pipeline()` - Concrete template (calls `_create_pipeline()` hook)
- `generate()` - Concrete template (calls `_build_prompts()`, `_build_pipeline_kwargs()`, etc.)
- Common functionality: device setup, LoRA management, cache clearing, metadata building
- Configuration-driven behavior via flags: `force_default_guidance`, `enable_debug_logging`, etc.

**Mixins** (`lib/models/mixins.py`) - Shared behaviors via multiple inheritance:
- `CLIPTokenLimitMixin` - 77-token limit handling for SDXL/SD15 models
- `DebugLoggingMixin` - Debug print statements (enabled via config)

**Concrete Models** - Minimal implementations (20-70 lines each):
- Only override `_create_pipeline()` (abstract, required)
- Optionally override hooks for model-specific behavior:
  - `_build_prompts()` - Custom prompt handling (token limiting, debug logging)
  - `_build_pipeline_kwargs()` - Model-specific parameters (callbacks, runtime detection)
  - `_apply_device_optimizations()` - Custom device optimizations
  - `_handle_special_prompt_requirements()` - Special prompt needs (Qwen)
- Everything else inherited from BaseModel and mixins

**Configuration Flags** (in `data/presets.json` settings):
- `force_default_guidance` - Force default guidance_scale (ignores parameter, Turbo models)
- `enable_debug_logging` - Enable debug print statements via DebugLoggingMixin
- `use_sequential_cpu_offload` - Use sequential vs model CPU offload (CUDA)
- `max_sequence_length` - Context length for Flux variants
- `load_in_8bit` - 8-bit quantization for Qwen

**Model Implementations**: ZImageTurboModel (73 lines), FluxModel (21 lines), Flux2KleinModel (21 lines), QwenImageModel (67 lines), SDXLModel (24 lines), SDXLTurboModel (48 lines), SD15Model (22 lines)

**Factory**: `ModelFactory.create_model()` in `lib/models/__init__.py` dispatches by pipeline type

### Key Code Paths

**Django app** — `cw/diffusion/`:
- `models.py` — ORM models: `DiffusionModel`, `LoraModel`, `Prompt`, `DiffusionJob`
- `admin.py` — Django Unfold admin (primary UI for creating prompts, queuing jobs, viewing results)
- `tasks.py` — Celery tasks: `generate_images_task(job_id)`, `enhance_prompt_task(prompt_id)`

**Supporting libraries** — `lib/`:
- `config.py` — `PresetsConfig` loads `data/presets.json`
- `prompt_enhancer.py` — Three enhancers: rule-based (`PromptEnhancer`), local LLM (`HFPromptEnhancer` using Qwen2.5-3B), Anthropic API (`LLMPromptEnhancer`)
- `civitai.py` — Auto-download LoRAs from CivitAI by AIR URN
- `loras/manager.py` — LoRA filtering by base architecture

### Data Flow
1. User creates a `Prompt` and `DiffusionJob` via Django admin
2. Admin `save_model()` hook auto-queues the job to Celery
3. Worker loads model (with warm cache), optionally loads LoRA (auto-downloads from CivitAI if AIR set)
4. Images generated and saved to `media/diffusion/`
5. Job status updated, results viewable in admin with image previews

### Configuration
- `data/presets.json` — Master config for models and LoRAs (synced to DB via `import_presets`)
- `.env` — Environment variables (DB credentials, API keys for Anthropic/CivitAI)
- `cw/settings.py` — Django settings including Celery config and Unfold admin setup

### Model-Specific Notes
| Model | Pipeline | Steps | CFG | Negative Prompt |
|-------|----------|-------|-----|-----------------|
| Z-Image Turbo | ZImagePipeline | 9 | 0.0 | No |
| Flux.1-dev | FluxPipeline | 28 | 3.5 | No |
| Qwen-Image-2512 | QwenImagePipeline | 50 | 4.5 | Yes |
| SDXL Turbo | AutoPipelineForText2Image | varies | varies | varies |
| Juggernaut XL v9 | StableDiffusionXLPipeline | 30 | 7.0 | Yes |
| DreamShaper XL Lightning | StableDiffusionXLPipeline | 4 | 2.0 | No |
| Realistic Vision v5.1 | StableDiffusionPipeline | 30 | 5.0 | Yes |

### Path Resolution
- Local models/LoRAs: path ends with `.safetensors` → resolved as `{base_model_path}/{path}`, loaded via `from_single_file()`
- HuggingFace models: path starts with `Hugginface:` or `Huggingface:` → prefix stripped, loaded via `from_pretrained()`

### Adding New Models (Post-Refactoring)

**Simple models** (most cases) - Just 10-20 lines:
1. Create `lib/models/newmodel.py` inheriting from `BaseModel`
2. Override `_create_pipeline()` to return your pipeline instance
3. Add to `lib/models/__init__.py` exports and `ModelFactory.create_model()`
4. Add model config to `data/presets.json` with appropriate flags
5. Run `uv run manage.py import_presets` to sync to database

**Example:**
```python
from diffusers import YourPipeline
from .base import BaseModel

class YourModel(BaseModel):
    def _create_pipeline(self):
        return YourPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
        )
```

**Models with special requirements**:
- **Token limiting** (CLIP 77-token): Inherit from `CLIPTokenLimitMixin` + `BaseModel`
- **Debug logging**: Inherit from `DebugLoggingMixin` + `BaseModel`
- **Custom prompt handling**: Override `_build_prompts(params: Dict) -> Dict`
- **Custom pipeline kwargs**: Override `_build_pipeline_kwargs(params: Dict, callback) -> Dict`
- **Custom device optimizations**: Override `_apply_device_optimizations() -> None`
- **Special prompt requirements**: Override `_handle_special_prompt_requirements(params: Dict) -> Dict`

## Environment & Dependencies
- Python 3.12+ managed via `uv`
- All models use `torch.bfloat16` precision
- Apple Silicon: MPS backend with `enable_sequential_cpu_offload()` and `enable_attention_slicing()`
- One model loaded at a time (module-level `_model_cache` in tasks.py)
- `torch.mps.empty_cache()` called after each generation
