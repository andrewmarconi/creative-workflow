# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QueerChaos 2 is a Python-based batch image generation tool using Flux2 diffusion models, optimized for Apple Silicon (M4 Mac with 48GB RAM). The project processes JSON input files containing multiple text prompts and generates high-quality images with resume capability and comprehensive metadata tracking.

## Environment & Dependencies

### Python Environment: uv (not conda or venv)
- Use `uv` for all Python environment management
- Install dependencies: `uv add <package>`
- When running Python from terminal, it should use the uv environment automatically

### Core Dependencies
- HuggingFace Diffusers (model loading)
- PyTorch with MPS backend OR MLX (Apple Silicon optimization)
- tqdm (progress tracking)
- Python 3.10+

### HuggingFace Authentication
The local machine should already have HuggingFace CLI authentication configured. The script relies on cached credentials.

## Architecture & Key Design Decisions

### Model Architecture
- **Diffusion Model**: `flux2_dev_fp8mixed` (fp8 quantization for memory efficiency)
- **Text Encoder**: `mistral_3_small_flux2_bf16` (bf16 precision)
- **LoRA**: Optional, can be HuggingFace ID or local `.safetensors` file path

### Apple Silicon Optimization Strategy
1. Prioritize MLX if diffusers supports it (native Apple Silicon)
2. Fallback to PyTorch with MPS backend
3. Use `torch.mps.set_per_process_memory_fraction(0.9)` for memory management
4. Clear cache between generations: `torch.mps.empty_cache()`
5. Load models once at startup, reuse for all generations (critical for performance)

### Flux2 Dev Best Practices (hardcoded)
- Resolution: 1024x1024
- Steps: 28 (speed) to 50 (quality) - recommend 28
- Guidance Scale: 3.5 (Flux2 Dev optimal)
- Scheduler: FlowMatchEulerDiscreteScheduler
- **No negative prompts** - Flux2 does not support them

## Data Flow & File Structure

### Input Flow
```
input.json → JSON Parser → Model Loader → Checkpoint Check → Generation Loop → Output Files
```

### Key Files
- `generate.py`: Main entry point
- `input.json`: Default input config (can override via CLI arg)
- Output directory structure:
  - `{prefix}_{001..count}.jpg`: Generated images
  - `generation_metadata.json`: All generation params, seeds, timestamps, errors
  - `.checkpoint.json`: Resume state tracking

### JSON Schema
Input requires `count`, `prompts`, `output_dir`. Optional: `lora` object.

```json
{
  "count": 3,
  "lora": {"name": "HF_ID or ./path/file.safetensors", "prompt": "suffix text"},
  "prompts": {"file_prefix": "prompt text", "prefix2": "prompt2"},
  "output_dir": "./outputs/batch"
}
```

## Resume & Checkpoint System

The checkpoint system enables interruption recovery:

1. Before generation, check `{output_dir}/.checkpoint.json`
2. If exists, load `completed_images` list
3. Skip images already in checkpoint
4. Update checkpoint after EACH successful generation
5. On errors: log in metadata but continue with other images

**To force regeneration**: Delete `.checkpoint.json`

## Critical Implementation Details

### LoRA Loading Logic
Detect local vs HuggingFace by checking:
- Path ends with `.safetensors`, OR
- File exists on filesystem
→ Load locally if true, else load from HuggingFace Hub

### Seed Management
- Generate random seed per image: `random.randint(0, 2**32 - 1)`
- Seeds NOT in filename (keeps names clean)
- Seeds saved in `generation_metadata.json` for reproducibility

### Error Handling Philosophy
- **Fatal errors** (exit code 1): Model loading, JSON validation
- **Non-fatal errors** (continue): Individual generation failures (OOM, invalid prompt)
- Log all errors in `generation_metadata.json` with status: "failed"
- Final exit code 2 if partial success (some failed, some succeeded)

### Image Naming Convention
- Format: `{file_prefix}_{index}.jpg`
- Index starts at 1
- Zero-pad to 3 digits if count > 99 (e.g., `portrait_001.jpg`)

## Running the Script

```bash
# Default (uses ./input.json)
python generate.py

# Custom input file
python generate.py configs/my_batch.json
```

## Memory Optimization Notes

M4 Mac has 48GB unified RAM, but models are large:
- Load models once at startup (not per-image)
- Use `low_cpu_mem_usage=True` when loading models
- Process prompts sequentially (no parallel batching to avoid OOM)
- fp8 quantization for diffusion model reduces memory footprint
- Cache models in HuggingFace cache directory (~/.cache/huggingface)

## Testing Checklist (from PRD)

When implementing or debugging, test these scenarios:
- Single prompt
- Multiple prompts
- With HuggingFace LoRA
- With local `.safetensors` LoRA
- Without LoRA
- Resume after interruption (Ctrl+C, then rerun)
- Error handling (invalid prompt, OOM simulation)

## Progress Display Format

Uses tqdm with custom postfix showing Success/Failed/Skipped counts:

```
Processing: 45%|████████████          | 9/20 [02:15<02:45, Success: 8, Failed: 1, Skipped: 0]
```

## Implementation Reference

See [prd.md](prd.md) for complete specification including:
- Detailed JSON schemas
- Full metadata file formats
- Example input/output
- Complete error handling matrix
- Performance optimization strategies
