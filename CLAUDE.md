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
uv run manage.py import_prompts                 # Bulk import prompts
uv run manage.py export_prompts                 # Export prompts to file
uv run manage.py preload_models                 # Pre-download models to HF cache
uv run manage.py createsuperuser                # Create admin user
```

### Testing
```bash
uv run python test_admin.py                     # Run admin tests
```

## Architecture

### Process Model
Four processes run concurrently (defined in `Procfile`, launched via `honcho start`):
1. **docker** — PostgreSQL 17 (port 5435) + Valkey (port 6379)
2. **django** — Django dev server (port 8000)
3. **worker** — Celery worker on `default` queue (image generation, GPU-intensive)
4. **enhancement** — Celery worker on `enhancement` queue (prompt enhancement via local LLM)

Celery uses `solo` pool (single-threaded) because MPS/CUDA contexts are not fork-safe.

### Key Code Paths

**Django app** — `cw/diffusion/`:
- `models.py` — ORM models: `DiffusionModel`, `LoraModel`, `Prompt`, `DiffusionJob`
- `admin.py` — Django Unfold admin (primary UI for creating prompts, queuing jobs, viewing results)
- `tasks.py` — Celery tasks: `generate_images_task(job_id)`, `enhance_prompt_task(prompt_id)`

**Model implementations** — `lib/models/`:
- `base.py` — `BaseModel` abstract class (device setup, LoRA loading, cache management)
- `zimageturbo.py`, `flux.py`, `qwen.py`, `sdxlturbo.py`, `sdxl.py`, `sd15.py` — Concrete implementations
- `__init__.py` — `ModelFactory.create_model()` dispatches by pipeline type

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

### Adding New Models
1. Create `lib/models/newmodel.py` inheriting from `BaseModel`, implement `load_pipeline()` and `generate()`
2. Add to `lib/models/__init__.py` exports and `ModelFactory.create_model()`
3. Add model config to `data/presets.json`
4. Run `uv run manage.py import_presets` to sync to database

## Environment & Dependencies
- Python 3.12+ managed via `uv`
- All models use `torch.bfloat16` precision
- Apple Silicon: MPS backend with `enable_sequential_cpu_offload()` and `enable_attention_slicing()`
- One model loaded at a time (module-level `_model_cache` in tasks.py)
- `torch.mps.empty_cache()` called after each generation
