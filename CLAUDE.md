# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QueerChaos 2 is a modular image generation application supporting multiple diffusion models (Z-Image Turbo, Flux.1-dev, Qwen-Image-2512) with a Gradio web interface. Optimized for Apple Silicon (M4 Mac with 48GB RAM) with dynamic LoRA filtering, model-specific optimal settings, and comprehensive metadata tracking.

## Environment & Dependencies

### Python Environment: uv (not conda or venv)
- Use `uv` for all Python environment management
- Install dependencies: `uv add <package>`
- Sync environment: `uv sync`
- Python 3.12+ required

### Core Dependencies
- **Gradio**: Web UI framework
- **HuggingFace Diffusers**: Model pipelines (ZImagePipeline, FluxPipeline, QwenImagePipeline)
- **PyTorch**: MPS backend for Apple Silicon
- **PEFT**: LoRA adapter support
- **Pillow, transformers, safetensors, accelerate**

### HuggingFace Authentication
The local machine has HuggingFace CLI authentication configured. For new setups: `huggingface-cli login`

## Architecture Overview

### Modular Design Pattern

The application uses a **factory pattern** with model-specific implementations:

```
main.py (Gradio UI)
    ↓
config.py (Loads presets.json)
    ↓
ModelFactory → creates model instances based on pipeline type
    ↓
models/base.py (Abstract BaseModel)
    ├── models/zimageturbo.py (Z-Image implementation)
    ├── models/flux.py (Flux.1-dev implementation)
    └── models/qwen.py (Qwen-Image implementation)

loras/manager.py (LoRA filtering by compatibility)
```

### Key Components

**[config.py](config.py)**:
- Loads and validates `presets.json`
- Handles both local `.safetensors` files and HuggingFace Hub IDs
- Provides model/LoRA lookup utilities
- Path resolution (local vs. HuggingFace)

**[models/base.py](models/base.py)**:
- Abstract base class for all models
- Common functionality: device setup, LoRA loading/unloading, cache management
- Defines interface: `load_pipeline()`, `generate()`

**[models/zimageturbo.py](models/zimageturbo.py)**, **[models/flux.py](models/flux.py)**, **[models/qwen.py](models/qwen.py)**:
- Model-specific implementations
- Encapsulate pipeline loading from `.safetensors` or HuggingFace
- Apply model-specific optimal settings
- Handle model-specific generation parameters

**[loras/manager.py](loras/manager.py)**:
- Filters LoRAs by model compatibility
- Resolves LoRA paths (relative to `base_model_path`)
- Provides strength and prompt suffix utilities

**[main.py](main.py)**:
- Gradio web interface
- ImageGenerator class manages model lifecycle
- Dynamic UI updates based on loaded model capabilities

**[presets.json](presets.json)**:
- Centralized configuration for all models and LoRAs
- Model-specific optimal settings (steps, guidance, scheduler, etc.)
- LoRA compatibility mappings

## Running the Application

### Start Gradio Web Interface
```bash
python main.py
```

The app will:
1. Load presets from `presets.json`
2. Display model selector dropdown
3. Auto-load default model (Z-Image Turbo) on startup
4. Launch Gradio UI at http://localhost:7860

### Workflow
1. Select model from dropdown
2. Click "Load Model" (or wait for auto-load)
3. LoRA dropdown auto-filters to compatible LoRAs
4. UI controls auto-configure for model capabilities
5. Generate images

## Model-Specific Settings (Research-Based)

### Z-Image Turbo
- **Pipeline**: `ZImagePipeline`
- **Steps**: 9 (results in 8 NFEs, optimal for turbo model)
- **Guidance Scale**: 0.0 (turbo model has internalized CFG)
- **Scheduler**: FlowMatchEulerDiscreteScheduler
- **Resolution**: 1024×1024
- **Negative Prompts**: NOT supported (distilled model)
- **Loading**: Local `.safetensors` via `from_single_file()`

### Flux.1-dev FP8 Mixed
- **Pipeline**: `FluxPipeline`
- **Steps**: 28 (optimal quality/speed balance)
- **Guidance Scale**: 3.5 (distilled CFG guidance)
- **Max Sequence Length**: 512
- **Resolution**: 1024×1024 (variable supported)
- **Negative Prompts**: NOT natively supported (distilled model)
- **Loading**: Local `.safetensors` via `from_single_file()`

### Qwen-Image-2512
- **Pipeline**: `QwenImagePipeline`
- **Steps**: 50 (CFG 4.5 + 50 steps is "golden config")
- **Guidance Scale**: 4.5 (`true_cfg_scale` in API)
- **Scheduler**: FlowMatchEulerDiscreteScheduler
- **Resolution**: Variable
- **Negative Prompts**: SUPPORTED (increases quality ~15%)
- **Loading**: HuggingFace Hub via `from_pretrained("Qwen/Qwen-Image-2512")`

## Apple Silicon Optimization Strategy

1. **Device Detection**: Auto-detect MPS (Apple Silicon), CUDA, or CPU
2. **Memory Management**:
   - `enable_sequential_cpu_offload()` for MPS
   - `enable_attention_slicing()` for all devices
   - `torch.mps.empty_cache()` after each generation
3. **Single Model Loading**: Load pipeline once, reuse for all generations
4. **bf16 Precision**: All models use `torch.bfloat16` for optimal Apple Silicon performance

## Adding New Models

Edit `presets.json`:

```json
{
  "label": "Model Display Name",
  "slug": "unique_slug",
  "path": "local/path.safetensors" or "Hugginface:org/model-id",
  "pipeline": "PipelineClassName",
  "settings": {
    "steps": 30,
    "guidance_scale": 7.0,
    "resolution": 1024,
    "scheduler": "SchedulerName" or null,
    "dtype": "bfloat16",
    "supports_negative_prompt": true,
    "max_sequence_length": 512 or null
  }
}
```

If the pipeline class doesn't exist in `models/`, create a new implementation:

1. Create `models/newmodel.py` inheriting from `BaseModel`
2. Implement `load_pipeline()` and `generate()`
3. Add to `models/__init__.py` exports
4. Update `ModelFactory.create_model()` in `main.py`

## Adding New LoRAs

Edit `presets.json`:

```json
{
  "label": "LoRA Display Name",
  "path": "loras/filename.safetensors",
  "compatibility": ["zimageturbo", "flux1_dev"],
  "prompt": "trigger words, style description",
  "settings": {"strength": 0.8},
  "air": "urn:air:optional:identifier"
}
```

LoRAs are stored relative to `base_model_path` from config.

## LoRA Compatibility System

- Each LoRA has a `compatibility` array listing model slugs
- `LoRAManager.get_compatible_loras(model_slug)` filters by compatibility
- UI dropdown auto-updates when model changes
- Only compatible LoRAs are shown/loadable

## Path Resolution Logic

**Local Models/LoRAs**:
- Path ends with `.safetensors`
- Resolved as: `{base_model_path}/{path}`
- Loaded via: `Pipeline.from_single_file(full_path)`

**HuggingFace Models**:
- Path starts with `Hugginface:` or `Huggingface:` prefix
- OR path contains `/` without `.safetensors` extension
- Prefix stripped, used directly as HF model ID
- Loaded via: `Pipeline.from_pretrained(model_id)`

## UI Behavior

### Dynamic Controls
- **Model Selector**: Dropdown populated from `presets.json` models
- **LoRA Selector**: Auto-filters to show only compatible LoRAs for selected model
- **Negative Prompt Field**: Shown only for models with `supports_negative_prompt: true`
- **Sliders**: Auto-update to model-specific default values on load

### Model Loading
- Click "Load Model" button or auto-loads on startup
- Progress bar shows: device setup → pipeline loading → optimization
- Status updates in real-time
- UI controls update automatically after load

### Generation
- Supports batch generation (count slider 1-10)
- Progress tracking per image and per step
- Metadata display shows all generation parameters
- Images saved to `{base_output_path}/{output_dir}/`

## Output Structure

```
outputs/{output_dir}/
├── {model_slug}_{timestamp}_{seed}_{001..count}.jpg
```

Filename format: `{model_slug}_{YYYYMMDD_HHMMSS}_{seed}_{index:03d}.jpg`

**Metadata Display** (in UI):
- Model name
- Full prompt (with LoRA suffix if applicable)
- Negative prompt (if used)
- Steps, guidance scale, resolution
- LoRA name (if applied)

## Configuration File: presets.json

**Structure**:
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

**Critical**:
- `base_model_path` must end with `/`
- Local model/LoRA paths are relative to this base
- All model settings are research-backed optimal defaults

## Error Handling

- **Model Loading Failures**: Display error in status, allow retry
- **LoRA Loading Failures**: Display error, continue without LoRA
- **Generation Failures**: Log error, continue with next image
- **Partial Success**: Report count of successful/failed generations

## Memory Considerations

M4 Mac with 48GB RAM:
- Load one model at a time (no parallel model loading)
- Sequential generation (no batching across prompts)
- Clear MPS cache after each generation
- FP8/bf16 quantization for memory efficiency
- Models cached in `~/.cache/huggingface/`

## Development Notes

### Model Implementation Checklist
When adding a new model class:
1. Inherit from `BaseModel`
2. Call `super().__init__(model_config, model_path)`
3. Implement `load_pipeline()`: handle both `.safetensors` and HuggingFace paths
4. Implement `generate()`: use model-specific parameters
5. Apply device-specific optimizations (MPS/CUDA/CPU)
6. Handle negative prompts correctly (check `supports_negative_prompt`)
7. Clear cache after generation

### LoRA Loading
- Use `BaseModel.load_lora()` for standard loading
- Strength is applied via `set_adapters()` if pipeline supports it
- Prompt suffix automatically appended during generation
- Unload previous LoRA before loading new one

### Testing Strategy
- Test model loading (local + HuggingFace)
- Test LoRA filtering (compatibility logic)
- Test generation with/without LoRA
- Test negative prompts (supported models only)
- Test batch generation
- Test UI state updates on model change
