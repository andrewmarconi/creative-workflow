# QueerChaos 2

Multi-model image generation application with Gradio web interface, supporting Z-Image Turbo, Flux.1-dev, and Qwen-Image-2512. Optimized for Apple Silicon with dynamic LoRA filtering and research-backed optimal settings.

## Features

- ✨ **Multi-Model Support**: Switch between Z-Image Turbo, Flux.1-dev, and Qwen-Image-2512
- 🎛️ **Dynamic LoRA Filtering**: Only shows compatible LoRAs for selected model
- 🎯 **Research-Based Defaults**: Optimal settings pre-configured per model
- 🖥️ **Gradio Web UI**: Interactive interface with real-time progress tracking
- 🔄 **Smart UI Updates**: Controls auto-configure based on model capabilities
- 📊 **Comprehensive Metadata**: Full generation parameters tracked and displayed
- 🍎 **Apple Silicon Optimized**: MPS backend with memory management
- 💾 **Flexible Model Loading**: Supports local .safetensors and HuggingFace Hub

## Quick Start

### 1. Setup Environment

This project uses `uv` for Python environment management.

```bash
# Sync dependencies
uv sync

# Authenticate with HuggingFace (if not already done)
huggingface-cli login
```

### 2. Configure Models & LoRAs

Edit [`presets.json`](presets.json) to configure:
- Model paths (local `.safetensors` or HuggingFace IDs)
- LoRA library with compatibility mappings
- Optimal generation settings per model

```json
{
  "config": {
    "base_model_path": "/path/to/models/",
    "base_output_path": "./outputs"
  },
  "models": [...],
  "loras": [...]
}
```

### 3. Launch All Services

All processes are defined in the [`Procfile`](Procfile) and managed with [honcho](https://github.com/nickstenning/honcho).

```bash
# Start everything (Docker, Django, Celery workers)
honcho start
```

This launches four processes with color-coded, interleaved output:

| Process | URL | Description |
|---------|-----|-------------|
| **docker** | — | PostgreSQL (port 5435) + Valkey (port 6379) |
| **django** | http://localhost:8000/admin/ | Django admin interface |
| **worker** | — | Celery worker for image generation (`default` queue) |
| **enhancement** | — | Celery worker for prompt enhancement (`enhancement` queue) |

Task results are visible in the Django admin under **Celery > Task Results**.

You can also start a subset of processes:

```bash
# Start only Docker and Django (no workers)
honcho start docker django
```

> **Note**: Docker services must be running before Django and the workers can connect. When using `honcho start`, all processes launch together — Celery will retry broker connections automatically.

## Usage

### Web Interface Workflow

1. **Select Model**: Choose from Z-Image Turbo, Flux.1-dev, or Qwen-Image-2512
2. **Load Model**: Click "Load Model" (auto-loads on startup)
3. **Configure Generation**:
   - Enter your prompt
   - Select compatible LoRA (dropdown auto-filters)
   - Adjust steps, guidance, resolution (defaults are optimal)
   - Set seed (or randomize)
   - Choose batch count (1-10 images)
4. **Generate**: Watch real-time progress with step-by-step updates
5. **Review**: View generated images and metadata in the UI

### Model Comparison

| Model | Speed | Quality | Steps | Guidance | Neg Prompts | Best For |
|-------|-------|---------|-------|----------|-------------|----------|
| **Z-Image Turbo** | ⚡ Fastest | Good | 9 | 0.0 | ❌ | Quick iterations, style tests |
| **Flux.1-dev** | ⚖️ Balanced | High | 28 | 3.5 | ❌ | General purpose, detailed images |
| **Qwen-Image-2512** | 🐢 Slower | Highest | 50 | 4.5 | ✅ | Final outputs, precise control |

## Configuration

### Adding Models

Add to `presets.json`:

```json
{
  "label": "My Model",
  "slug": "my_model",
  "path": "path/to/model.safetensors",
  "pipeline": "PipelineClassName",
  "settings": {
    "steps": 30,
    "guidance_scale": 7.0,
    "resolution": 1024,
    "supports_negative_prompt": true
  }
}
```

### Adding LoRAs

Add to `presets.json`:

```json
{
  "label": "My LoRA",
  "path": "loras/my-lora.safetensors",
  "compatibility": ["zimageturbo", "flux1_dev"],
  "prompt": "trigger words, style description",
  "settings": {"strength": 0.8}
}
```

LoRAs will automatically appear in the dropdown for compatible models only.

## Output Structure

Generated images are saved to:

```
outputs/{output_dir}/
├── {model_slug}_{timestamp}_{seed}_001.jpg
├── {model_slug}_{timestamp}_{seed}_002.jpg
└── ...
```

**Filename Format**: `{model_slug}_{YYYYMMDD_HHMMSS}_{seed}_{index:03d}.jpg`

**Metadata** is displayed in the UI after generation:
- Model used
- Full prompt (with LoRA suffix)
- Negative prompt (if supported)
- Steps, guidance scale, resolution
- LoRA applied (if any)
- Seed for reproducibility

## Architecture

```
main.py                    # Gradio web interface
├── config.py              # Loads presets.json
├── models/                # Model implementations
│   ├── base.py           # Abstract BaseModel
│   ├── zimageturbo.py    # Z-Image Turbo
│   ├── flux.py           # Flux.1-dev
│   └── qwen.py           # Qwen-Image-2512
└── loras/
    └── manager.py         # LoRA filtering & loading
```

See [`CLAUDE.md`](CLAUDE.md) for detailed architecture documentation.

## System Requirements

- **Hardware**: M4 Mac with 48GB RAM (or similar Apple Silicon)
- **Software**: Python 3.12+, `uv` package manager
- **Storage**: ~15GB for model cache (`~/.cache/huggingface/`)
- **Models**: Local `.safetensors` files or HuggingFace Hub access

## Model-Specific Notes

### Z-Image Turbo
- **Speed**: ~4 seconds per image on RTX A6000
- **Settings**: 9 steps, guidance 0.0 (distilled model)
- **LoRAs**: 8 compatible LoRAs included (pen & ink, manga, sketches, etc.)
- **Use Case**: Quick iterations, style exploration

### Flux.1-dev FP8 Mixed
- **Speed**: Moderate (28 steps optimal)
- **Settings**: Guidance 3.5 (distilled CFG), max_sequence_length 512
- **Format**: Local FP8 quantized `.safetensors`
- **Use Case**: Balanced quality/speed, general purpose

### Qwen-Image-2512
- **Speed**: Slower (50 steps)
- **Settings**: Guidance 4.5 (true_cfg_scale), supports negative prompts
- **Format**: HuggingFace Hub download
- **Use Case**: Highest quality, precise control with negative prompts

## Development

```bash
# Start all services
honcho start

# Start individual processes
honcho start django worker

# Add new dependency
uv add package-name

# Sync dependencies
uv sync

# Run Django management commands
uv run manage.py migrate
uv run manage.py import_presets
uv run manage.py import_prompts --file data/coloringbook_prompts.txt --style coloring-book
uv run manage.py createsuperuser
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Architecture & development guide
- **[presets.json](presets.json)** - Model & LoRA configuration
- **Legacy batch processor** - See `_PARKED/` directory

## Troubleshooting

**Model won't load?**
- Check `base_model_path` in `presets.json`
- Verify `.safetensors` files exist for local models
- Ensure HuggingFace authentication for Hub models

**LoRA not appearing?**
- Check `compatibility` array matches model `slug`
- Verify LoRA path is relative to `base_model_path`
- Ensure `.safetensors` file exists

**Out of memory?**
- Use Z-Image Turbo (9 steps) or reduce resolution
- Close other applications
- Only one model loads at a time (by design)

## License

TBD
