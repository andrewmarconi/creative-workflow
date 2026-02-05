# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Creative Workflow is a Django + Celery application for multi-model diffusion image generation. It uses Django Unfold for the admin UI, PostgreSQL for storage, and Valkey/Redis as the Celery broker. Models supported: Z-Image Turbo, Flux.1-dev, Flux.2 Klein, Qwen-Image-2512, SDXL Turbo, DreamShaper XL Lightning, Juggernaut XL v9, Realistic Vision v5.1.

## Commands

### Setup & Run
```bash
uv sync                          # Install/sync dependencies
honcho start                     # Start all processes (Docker, Django, Celery workers)
honcho start docker django       # Start subset of processes (without workers)
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
uv run manage.py import_adaptations             # Import adaptations.json into prompts/jobs
uv run manage.py preload_models                 # Pre-download models to HF cache
uv run manage.py createsuperuser                # Create admin user
```

### Testing
```bash
uv run python test_admin.py                     # Run admin tests
```

### Documentation
```bash
cd docs && make html                            # Build HTML documentation
open docs/_build/html/index.html                # View documentation
cd docs && make clean                           # Clean build artifacts
```

### Observability & Logging
```bash
# View logs locally (JSON format)
tail -f logs/tasks.log                          # Task execution logs (all workers)
tail -f logs/worker_default.log                 # Image generation worker only
tail -f logs/worker_enhancement.log             # Prompt enhancement worker only
tail -f logs/django.log                         # Django server logs
tail -f logs/celery.log                         # Celery general logs

# Parse JSON logs with jq
cat logs/tasks.log | jq 'select(.levelname == "ERROR")'

# Grafana Loki - Log aggregation & search
# 1. Start docker-compose (includes Loki, Alloy, Grafana)
# 2. Logs are automatically collected from logs/*.log
# 3. Access Grafana UI at http://localhost:3000
# 4. Navigate to Explore → select Loki data source
# 5. Query examples:
#    - {job="django"} - All Django logs
#    - {job="celery"} | json | level="ERROR" - Celery errors
#    - {job="tasks"} |= "image generation" - Search for text
```

## Architecture

### Process Model
Four processes run concurrently (defined in `Procfile`, launched via `honcho start`):
1. **docker** — PostgreSQL 17 (port 5435) + Valkey (port 6379) + Grafana/Loki (log aggregation)
2. **django** — Django dev server (port 8000)
3. **worker** — Celery worker on `default` queue (image generation, GPU-intensive)
4. **enhancement** — Celery worker on `enhancement` queue (prompt enhancement via local LLM)

Celery uses `solo` pool (single-threaded) because MPS/CUDA contexts are not fork-safe.

**Grafana + Loki** (via `docker-compose.yml`, always enabled):
- **Loki** (port 3100) — Log aggregation backend, stores all logs
- **Alloy** — Unified observability collector, ships logs from `logs/*.log` to Loki
- **Grafana** (port 3000) — Web UI for searching and viewing logs

Access Grafana UI at http://localhost:3000 (anonymous login enabled for local dev).

### Project Structure

Uses **src layout** for proper Python packaging:
```
creative-workflow/
├── src/cw/              # Main package (Django project + apps + lib)
│   ├── diffusion/       # Django app for image generation
│   │   └── templates/   # App-specific admin templates
│   ├── tvspots/         # Django app for TV spot management
│   │   └── templates/   # App-specific admin templates
│   └── lib/             # Supporting library modules
│       ├── models/      # Diffusion model implementations
│       ├── loras/       # LoRA management
│       └── *.py         # Utilities (civitai, prompt_enhancer, etc.)
├── manage.py            # Django management script
├── staticfiles/         # collectstatic output (not source files)
├── media/               # User-uploaded content
├── data/                # Configuration files (presets.json)
└── logs/                # Application logs
```

### Model Architecture (Refactored 2026-02)

**Template Method Pattern** - Eliminates 70%+ code duplication:

**BaseModel** (`src/cw/lib/models/base.py`) - Abstract base with concrete template methods:
- `load_pipeline()` - Concrete template (calls `_create_pipeline()` hook)
- `generate()` - Concrete template (calls `_build_prompts()`, `_build_pipeline_kwargs()`, etc.)
- Common functionality: device setup, LoRA management, cache clearing, metadata building
- Configuration-driven behavior via flags: `force_default_guidance`, `enable_debug_logging`, etc.

**Mixins** (`src/cw/lib/models/mixins.py`) - Shared behaviors via multiple inheritance:
- `CompelPromptMixin` - Long prompt handling (>77 tokens) and prompt weighting for CLIP-based models using Compel library
- `CLIPTokenLimitMixin` - (Legacy) 77-token truncation for SDXL/SD15 models (replaced by CompelPromptMixin)
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

**Model Implementations**: ZImageTurboModel, FluxModel, Flux2KleinModel, QwenImageModel, SDXLModel, SDXLTurboModel, SD15Model

**Factory**: `ModelFactory.create_model()` in `src/cw/lib/models/__init__.py` dispatches by pipeline type

### Key Code Paths

**Django app** — `src/cw/diffusion/`:
- `models.py` — ORM models: `DiffusionModel`, `LoraModel` (with theme field for categorization), `Prompt`, `DiffusionJob`
- `admin.py` — Django Unfold admin (primary UI for creating prompts, queuing jobs, viewing results)
- `tasks.py` — Celery tasks: `generate_images_task(job_id)`, `enhance_prompt_task(prompt_id)`

**Supporting libraries** — `src/cw/lib/`:
- `config.py` — `PresetsConfig` loads `data/presets.json`
- `prompt_enhancer.py` — Three enhancers: rule-based (`PromptEnhancer`), local LLM (`HFPromptEnhancer` using Qwen2.5-3B), Anthropic API (`LLMPromptEnhancer`)
- `civitai.py` — Auto-download LoRAs from CivitAI by AIR URN
- `loras/manager.py` — LoRA filtering by base architecture and optional theme (e.g., 'anime', 'photorealistic', 'fantasy')

### Data Flow
1. User creates a `Prompt` and `DiffusionJob` via Django admin
2. Admin `save_model()` hook auto-queues the job to Celery
3. Worker loads model (with warm cache), optionally loads LoRA (auto-downloads from CivitAI if AIR set)
4. Images generated and saved to `media/diffusion/`
5. Job status updated, results viewable in admin with image previews

### Configuration
- `data/presets.json` — Master config for models and LoRAs (synced to DB via `import_presets`)
- `.env` — Environment variables:
  - **Required**: `POSTGRES_*`, `VALKEY_*`, `DJANGO_SECRET_KEY`
  - **Optional**: `ANTHROPIC_API_KEY` (for LLM prompt enhancement), `CIVITAI_API_KEY` (for auto-downloading LoRAs), `MODEL_BASE_PATH` (base directory for local `.safetensors` files)
- `src/cw/settings.py` — Django settings including Celery config and Unfold admin setup
- `grafana/provisioning/` — Grafana datasource/dashboard provisioning (auto-configures Loki on startup)

### Model-Specific Notes
| Model | Pipeline | Steps | CFG | Negative Prompt | Architecture |
|-------|----------|-------|-----|-----------------|--------------|
| Z-Image Turbo | ZImagePipeline | 9 | 0.0 | No | zimage |
| Flux.1-dev | FluxPipeline | 28 | 3.5 | No | flux1 |
| Flux.2 Klein | FluxPipeline | 28 | 3.5 | No | flux1 |
| Qwen-Image-2512 | QwenImagePipeline | 50 | 4.5 | Yes | qwen |
| SDXL Turbo | AutoPipelineForText2Image | 4 | 0.0 | No | sdxl |
| Juggernaut XL v9 | StableDiffusionXLPipeline | 30 | 7.0 | Yes | sdxl |
| DreamShaper XL Lightning | StableDiffusionXLPipeline | 4 | 2.0 | No | sdxl |
| Realistic Vision v5.1 | StableDiffusionPipeline | 30 | 5.0 | Yes | sd15 |

### Path Resolution
- Local models/LoRAs: path ends with `.safetensors` → resolved as `{base_model_path}/{path}`, loaded via `from_single_file()`
- HuggingFace models: path starts with `Hugginface:` or `Huggingface:` → prefix stripped, loaded via `from_pretrained()`

### Adding New Models (Post-Refactoring)

**Simple models** (most cases) - Just 10-20 lines:
1. Create `src/cw/lib/models/newmodel.py` inheriting from `BaseModel`
2. Override `_create_pipeline()` to return your pipeline instance
3. Add to `src/cw/lib/models/__init__.py` exports and `ModelFactory.create_model()`
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
- **Long prompts + prompt weighting** (CLIP-based models): Inherit from `CompelPromptMixin` + `BaseModel` (handles >77 tokens via Compel, supports `(word:weight)` syntax)
- **Token truncation** (legacy): Inherit from `CLIPTokenLimitMixin` + `BaseModel` (simple 77-token truncation, deprecated in favor of CompelPromptMixin)
- **Debug logging**: Inherit from `DebugLoggingMixin` + `BaseModel`
- **Custom prompt handling**: Override `_build_prompts(params: Dict) -> Dict`
- **Custom pipeline kwargs**: Override `_build_pipeline_kwargs(params: Dict, callback) -> Dict`
- **Custom device optimizations**: Override `_apply_device_optimizations() -> None`
- **Special prompt requirements**: Override `_handle_special_prompt_requirements(params: Dict) -> Dict`

### Compel Prompt Features (SDXL, SD15)

CLIP-based models (SDXL, SD15) now use [Compel](https://github.com/damian0815/compel) for advanced prompt handling:

**Long Prompts**: No 77-token limit - prompts are automatically chunked and embeddings concatenated:
```python
# This long prompt works without truncation:
prompt = """a highly detailed, photorealistic landscape painting of a serene mountain
valley at sunset, with dramatic lighting, golden hour atmosphere, misty background,
lush green meadows in the foreground, snow-capped peaks in the distance"""
```

**Prompt Weighting**: Emphasize or de-emphasize concepts using `(word:weight)` syntax:
```python
# Increase emphasis (>1.0) or decrease (<1.0):
prompt = "a (beautiful:1.3) landscape with (dramatic lighting:1.5), avoiding (blur:0.5)"
```

**LoRA Integration**: Trigger words are automatically appended without truncation concerns.

## Environment & Dependencies
- Python 3.12+ managed via `uv`
- All models use `torch.bfloat16` precision
- Apple Silicon: MPS backend with `enable_sequential_cpu_offload()` and `enable_attention_slicing()`
- One model loaded at a time (module-level `_model_cache` in tasks.py)
- `torch.mps.empty_cache()` called after each generation
