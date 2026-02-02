# Creative Workflow

Multi-model diffusion image generation application built with Django, Celery, and Django Unfold. Supports seven models across four architectures, with dynamic LoRA compatibility, CivitAI auto-download, and prompt enhancement via local LLM or Anthropic API.

## Features

- **Multi-Model Support**: Z-Image Turbo, Flux.1-dev, Flux.2 Klein, SDXL Turbo, Juggernaut XL, DreamShaper XL Lightning, Realistic Vision v5.1
- **Django Admin UI**: Full workflow via Django Unfold — create prompts, queue jobs, view results with image previews
- **Dynamic LoRA Filtering**: LoRAs filtered by base architecture (SDXL, SD 1.5, Flux.1, etc.)
- **CivitAI Auto-Download**: LoRAs with AIR URNs are downloaded automatically on first use
- **Prompt Enhancement**: Rule-based, local LLM (Qwen2.5-3B), or Anthropic API enhancers
- **Apple Silicon Optimized**: MPS backend with sequential CPU offload and attention slicing
- **Flexible Model Loading**: Local `.safetensors` files or HuggingFace Hub models

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
uv sync

# Copy environment file and configure
cp .env.example .env  # Edit with your DB credentials, API keys

# Authenticate with HuggingFace (for Hub models)
huggingface-cli login
```

### 2. Configure Models & LoRAs

Edit [`data/presets.json`](data/presets.json) to configure models and LoRAs, then sync to the database:

```bash
uv run manage.py migrate
uv run manage.py import_presets
uv run manage.py createsuperuser
```

### 3. Launch All Services

All processes are defined in the [`Procfile`](Procfile) and managed with [honcho](https://github.com/nickstenning/honcho).

```bash
honcho start
```

| Process | Description |
|---------|-------------|
| **docker** | PostgreSQL (port 5435) + Valkey (port 6379) |
| **django** | Django dev server at http://localhost:8000/admin/ |
| **worker** | Celery worker for image generation (`default` queue) |
| **enhancement** | Celery worker for prompt enhancement (`enhancement` queue) |

```bash
# Start a subset of processes
honcho start docker django
```

## Usage

1. Create a **Prompt** in the Django admin
2. Create **DiffusionJobs** from a prompt (select model, optional LoRA, parameters)
3. Jobs are auto-queued to Celery on save
4. Generated images saved to `media/diffusion/` and viewable in admin

## Model Comparison

| Model | Architecture | Steps | CFG | Neg Prompt | Best For |
|-------|-------------|-------|-----|------------|----------|
| Z-Image Turbo | Lumina/S3-DiT | 9 | 0.0 | No | Quick iterations |
| Flux.1-dev | Flux.1 | 28 | 3.5 | No | General purpose |
| Flux.2 Klein | Flux.1 | 28 | 3.5 | No | Lightweight Flux |
| SDXL Turbo | SDXL | 4 | 0.0 | No | Fast SDXL |
| Juggernaut XL v9 | SDXL | 30 | 7.0 | Yes | Photorealistic |
| DreamShaper XL Lightning | SDXL | 4 | 2.0 | No | Fast stylized |
| Realistic Vision v5.1 | SD 1.5 | 30 | 5.0 | Yes | Photorealistic (SD 1.5) |

## Configuration

### Adding Models

1. Add model config to `data/presets.json`
2. Create `lib/models/newmodel.py` inheriting from `BaseModel`
3. Register in `lib/models/__init__.py` `ModelFactory.create_model()`
4. Run `uv run manage.py import_presets`

### Adding LoRAs

Add to `data/presets.json` with a `base_architecture` field for compatibility:

```json
{
  "label": "My LoRA",
  "path": "loras/my-lora.safetensors",
  "base_architecture": "sdxl",
  "prompt": "trigger words",
  "settings": {"strength": 0.8}
}
```

LoRAs can also specify a CivitAI `air` URN for auto-download instead of a local path.

## Architecture

```
cw/diffusion/       # Django app
  models.py                 # DiffusionModel, LoraModel, Prompt, DiffusionJob
  admin.py                  # Django Unfold admin (primary UI)
  tasks.py                  # Celery tasks for generation and enhancement
lib/models/                 # Model implementations
  base.py                   # Abstract BaseModel
  zimageturbo.py, flux.py, flux2klein.py, qwen.py,
  sdxlturbo.py, sdxl.py, sd15.py
lib/
  config.py                 # Loads data/presets.json
  prompt_enhancer.py        # Rule-based, HF, and Anthropic enhancers
  civitai.py                # CivitAI LoRA downloader
  loras/manager.py          # LoRA filtering by base architecture
```

See [`CLAUDE.md`](CLAUDE.md) for detailed architecture documentation.

## System Requirements

- **Python**: 3.12+ via `uv`
- **Services**: PostgreSQL, Valkey/Redis (provided via Docker Compose)
- **GPU**: Apple Silicon (MPS) or CUDA
- **Storage**: ~15-30GB for model cache (`~/.cache/huggingface/`)

## Development

```bash
honcho start                              # Start all services
uv run manage.py migrate                  # Run migrations
uv run manage.py import_presets           # Sync presets.json to DB
uv run manage.py preload_models           # Pre-download models to HF cache
uv run manage.py import_prompts           # Bulk import prompts
uv run manage.py export_prompts           # Export prompts
```

## Troubleshooting

**Model won't load?**
- Verify HuggingFace authentication for Hub models
- Check `MODEL_BASE_PATH` in `.env` for local `.safetensors` models

**LoRA not appearing?**
- Check `base_architecture` matches the model's architecture
- Verify the file exists or the AIR URN is valid for CivitAI download

**Out of memory?**
- Use a turbo/lightning model with fewer steps
- Only one model loads at a time (by design)
- `torch.mps.empty_cache()` runs after each generation

## License

TBD
