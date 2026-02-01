# QueerChaos 2

Batch image generation using Flux2 diffusion models, optimized for Apple Silicon (M4 Mac).

## Setup

This project uses `uv` for Python environment management.

### 1. Project is Already Initialized

The project has been initialized with `uv init` and dependencies are tracked in `pyproject.toml`.

### 2. Sync Dependencies

```bash
uv sync
```

This will create a virtual environment and install all dependencies from the lock file.

### 3. Authenticate with HuggingFace

```bash
huggingface-cli login
```

## Usage

### Basic Usage

```bash
python generate.py
```

This will use the default `./input.json` file.

### Custom Input File

```bash
python generate.py my_config.json
```

## Input JSON Format

```json
{
  "count": 3,
  "lora": {
    "name": "fofr/flux-80s-cyberpunk",
    "prompt": "in 80s cyberpunk style"
  },
  "prompts": {
    "cityscape": "A futuristic cityscape at sunset, vibrant colors",
    "portrait": "Portrait of a cyberpunk hacker, neon lighting"
  },
  "output_dir": "./outputs/batch1"
}
```

### Fields

- **count** (required): Number of images to generate per prompt
- **prompts** (required): Dictionary of `file_prefix: prompt_text` pairs
- **output_dir** (required): Where to save generated images
- **lora** (optional): LoRA configuration
  - **name**: HuggingFace model ID or local `.safetensors` file path
  - **prompt**: Text to append to each prompt

## Output

Generated images will be saved in the specified `output_dir`:

```
outputs/batch1/
├── .checkpoint.json              # Resume state (auto-generated)
├── generation_metadata.json      # Complete generation metadata
├── cityscape_001.jpg
├── cityscape_002.jpg
├── cityscape_003.jpg
├── portrait_001.jpg
├── portrait_002.jpg
└── portrait_003.jpg
```

## Resume Capability

If generation is interrupted, simply run the same command again. The script will:
- Check for `.checkpoint.json` in the output directory
- Skip already-generated images
- Continue from where it left off

To force regeneration, delete `.checkpoint.json`.

## Development Status

- ✅ Phase 1: Setup & Model Loading
- ⏳ Phase 2: Core Generation
- ⏳ Phase 3: Progress & Metadata
- ⏳ Phase 4: Resume & Error Handling
- ⏳ Phase 5: Testing

## Documentation

- [CLAUDE.md](CLAUDE.md) - Developer guidance for Claude Code
- [prd.md](prd.md) - Complete implementation specification

## System Requirements

- M4 Mac with 48GB RAM (or similar Apple Silicon)
- Python 3.10+
- ~15GB disk space for models (cached in `~/.cache/huggingface/`)

## License

TBD
