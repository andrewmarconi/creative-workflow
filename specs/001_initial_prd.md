# Creative Workflow Library

**A Collection of Modules to Enable Rapid Generative AI Workflows**

---

## 1. Image Generation

### 1.1 Multi-Model Support

**Capability:** Generate images using any of 8+ supported diffusion models from a single unified interface.

**Functional Requirements:**

- Load any supported model by name/slug
- Generate images from text prompts with configurable parameters
- Support models from both HuggingFace Hub and local `.safetensors` files
- Automatically detect and use available hardware (Apple Silicon MPS, NVIDIA CUDA, CPU)
- Keep only one model loaded at a time to conserve memory
- Cache loaded models to avoid reload delays between generations
- Return generated image as PIL Image object with metadata dictionary

**User-Facing Parameters:**

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| Prompt | Text description of desired image | "a cat sitting on a windowsill" |
| Negative prompt | What to avoid (model-dependent) | "blurry, low quality" |
| Steps | Inference iterations | 4–50 (model-specific default) |
| Guidance scale | Prompt adherence strength | 0.0–7.5 (model-specific default) |
| Width | Output width in pixels | 512–2048 (constrained by `max_pixels`) |
| Height | Output height in pixels | 512–2048 (constrained by `max_pixels`) |
| Seed | Reproducibility control | Any integer, or None for random |
| CLIP skip | Skip text encoder layers | 1–3 (CLIP-based models only) |

**Generation Output:**

Returns a tuple of `(PIL.Image.Image, dict)` containing:

| Metadata Field | Description |
|----------------|-------------|
| `model` | Model label used for generation |
| `prompt` | Final prompt (with LoRA suffixes applied) |
| `negative_prompt` | Final negative prompt (if supported) |
| `steps` | Inference steps used |
| `guidance_scale` | CFG scale used |
| `width` / `height` | Output dimensions |
| `seed` | Random seed used |
| `lora` | LoRA label if applied, else None |
| `max_sequence_length` | Token context length (Flux/Qwen only) |

---

### 1.2 Progress Tracking

**Capability:** Receive real-time progress updates during model loading and image generation.

**Functional Requirements:**

- Accept optional `progress_callback` function for both `load_pipeline()` and `generate()`
- Callback receives `(progress: float, desc: str)` where progress is 0.0–1.0
- **Loading stages:** Device setup → Pipeline loading → Optimization
- **Generation stages:** Step-by-step progress (e.g., "Step 5/28")
- Callback support varies by model (Z-Image Turbo, Qwen fully supported)

**Callback Signature:**

```python
def progress_callback(progress: float, desc: str) -> None:
    """
    progress: 0.0 to 1.0 indicating completion percentage
    desc: Human-readable description of current stage
    """
    print(f"[{int(progress * 100):3d}%] {desc}")
```

---

### 1.3 Device Optimization

**Capability:** Automatically optimize for the user's hardware without manual configuration.

**Functional Requirements:**

- **Apple Silicon (MPS):**
  - Keep VAE in float32 to prevent black/corrupted images
  - Enable attention slicing for memory efficiency
  - Enable VAE slicing and tiling for large images
  - Move entire pipeline to MPS device
- **NVIDIA CUDA:**
  - Use CPU offloading to handle models larger than VRAM
  - Configurable: `use_sequential_cpu_offload` (slower, less VRAM) vs model-level offload
  - Enable attention slicing
- **CPU Fallback:** Run on machines without GPU (slower but functional)
- Automatically clear GPU memory cache after each generation

---

### 1.4 Model-Specific Behaviors

**Capability:** Each model operates with its optimal settings automatically applied.

**Functional Requirements:**

- **Turbo/Distilled models** (Z-Image Turbo, SDXL Turbo, DreamShaper XL Lightning):
  - Force `guidance_scale` to model default (ignores user override)
  - Use model-specific scheduler (Euler, DPMSolver, FlowMatch)
- **CLIP-based models** (SDXL, SD 1.5):
  - Handle 77-token prompt limit via truncation or Compel embeddings
  - Support CLIP skip parameter
- **Flux models:**
  - Support extended context length (512 tokens via `max_sequence_length`)
- **Qwen-Image:**
  - Support 8-bit quantization for memory efficiency
  - Handle empty negative prompts (requires space character)
  - Runtime parameter detection for callback support

---

### 1.5 Resolution Constraints

**Capability:** Enforce per-model resolution limits to prevent out-of-memory errors.

**Functional Requirements:**

- Each model defines `max_pixels` constraint (width × height limit)
- Each model defines `default_width` and `default_height` (can be non-square)
- Validation prevents exceeding model's maximum resolution

**Per-Model Constraints:**

| Model | Default Size | Max Pixels | Max Resolution |
|-------|--------------|------------|----------------|
| SD 1.5 (Realistic Vision) | 512×768 | 393,216 | ~512×768 |
| SDXL Turbo | 512×512 | 262,144 | 512×512 |
| SDXL (Juggernaut, DreamShaper) | 1024×1024 | 1,048,576 | 1024×1024 |
| Z-Image Turbo | 1024×1024 | 1,048,576 | 1024×1024 |
| Flux.1-dev | 1024×1024 | 2,097,152 | ~1024×2048 |
| Qwen-Image-2512 | 1328×1328 | 14,680,064 | Up to 4K |

---

## 2. LoRA Adapter System

### 2.1 LoRA Loading & Application

**Capability:** Modify model outputs using LoRA adapters (Low-Rank Adaptations) to achieve specific styles, subjects, or qualities.

**Functional Requirements:**

- Load LoRA `.safetensors` files dynamically without reloading base model
- Apply configurable LoRA strength (0.0–1.0)
- Support named adapters via `adapter_name` parameter
- Automatically append LoRA trigger words (`prompt` field) to prompts
- Automatically append LoRA negative prompts when applicable
- Override `guidance_scale` and `clip_skip` when LoRA specifies it
- Unload LoRAs cleanly to return to base model behavior
- Re-apply device-specific fixes after LoRA operations (MPS float32 VAE)

**LoRA Configuration Fields:**

| Field | Description | Required |
|-------|-------------|----------|
| `label` | Display name | Yes |
| `base_architecture` | Compatible architecture (sd15, sdxl, flux1, etc.) | Yes |
| `path` | File path relative to `base_model_path` | Yes (if local) |
| `air` | CivitAI AIR URN for auto-download | No |
| `prompt` | Trigger words to append to prompt | No |
| `negative_prompt` | Words to append to negative prompt | No |
| `theme` | Categorization (anime, photorealistic, fantasy, etc.) | No |
| `is_active` | Enable/disable flag | No (default: true) |
| `settings.strength` | Recommended LoRA strength | No (default: 1.0) |
| `settings.guidance_scale` | Override CFG scale | No |
| `settings.clip_skip` | Override CLIP skip | No |
| `notes` | Description and metadata | No |

---

### 2.2 LoRA Compatibility Filtering

**Capability:** Only show LoRAs compatible with the currently selected model.

**Functional Requirements:**

- Filter LoRAs by `base_architecture` (sd15, sdxl, flux1, zimage, qwen)
- Filter LoRAs by `theme` (anime, photorealistic, fantasy, sketch, etc.)
- Generate dropdown choices for UI with "None (No LoRA)" option
- Validate that LoRA file exists before attempting load
- Report recommended strength per LoRA
- Check `is_active` flag to exclude disabled LoRAs

**Base Architecture Mapping:**

| Architecture | Compatible Models |
|--------------|-------------------|
| `sd15` | Realistic Vision v5.1, other SD 1.5 checkpoints |
| `sdxl` | Juggernaut XL, DreamShaper XL, SDXL Turbo |
| `flux1` | Flux.1-dev |
| `zimage` | Z-Image Turbo |
| `qwen` | Qwen-Image-2512 |

---

## 3. Prompt Enhancement

### 3.1 Rule-Based Enhancement

**Capability:** Transform simple prompts into detailed, high-quality prompts optimized for diffusion models—without any external dependencies.

**Functional Requirements:**

- Accept simple prompt like "a cat" and output detailed prompt with quality tags
- Auto-detect style from keywords (photography, artistic, realistic, cinematic, coloring-book)
- Add appropriate quality tags ("masterpiece", "best quality", "highly detailed")
- Add style-specific descriptors ("DSLR", "bokeh" for photography; "line art", "clear outlines" for coloring book)
- Add technical enhancements ("sharp focus", "rich colors")
- Generate matching negative prompt ("blurry", "low quality", "watermark")
- Support LoRA trigger words (prepended to enhanced prompt)
- Configurable creativity level (0.0–1.0) controls how many enhancements added

**Supported Styles:**

| Style | Descriptors |
|-------|-------------|
| `photography` | DSLR, bokeh, lighting terms |
| `artistic` | concept art, trending on artstation |
| `realistic` | photorealistic, hyperrealistic |
| `cinematic` | movie still, dramatic lighting |
| `coloring-book` | line art, clear outlines, no shading |
| `auto` | detect from prompt keywords |

---

### 3.2 Local LLM Enhancement (HuggingFace)

**Capability:** Use a local language model to generate sophisticated, context-aware prompt expansions—no API costs, works offline.

**Functional Requirements:**

- Load configurable HuggingFace model (default: Qwen2.5-3B-Instruct)
- Auto-detect device (MPS, CUDA, CPU)
- Generate creative, detailed prompts using chat-style LLM inference
- Return structured JSON with enhanced_prompt and negative_prompt
- Fall back to rule-based if model fails to load
- Support same style and trigger word options as rule-based

**Recommended Models:**

| Model | Notes |
|-------|-------|
| `Qwen/Qwen2.5-3B-Instruct` | Default, efficient |
| `gokaygokay/Flux-Prompt-Enhance` | Specialized for image prompts |
| `microsoft/Phi-3.5-mini-instruct` | Lightweight |
| `Qwen/Qwen2.5-7B-Instruct` | Higher quality |

---

### 3.3 API-Based Enhancement (Anthropic)

**Capability:** Use Claude API for highest-quality prompt expansions.

**Functional Requirements:**

- Accept Anthropic API key
- Use Claude 3.5 Sonnet (configurable model)
- Generate prompts using same guidelines as HF enhancer
- Return structured JSON output
- Fall back to rule-based on API failure

---

### 3.4 Batch Processing

**Capability:** Enhance multiple prompts from a file.

**Functional Requirements:**

- Read prompts from text file (one per line)
- Skip comments (lines starting with `#`)
- Show progress during batch processing
- Output results to JSON file or stdout
- Include settings metadata in output

---

## 4. Long Prompt & Prompt Weighting (Compel)

### 4.1 Long Prompts

**Capability:** Use prompts longer than CLIP's 77-token limit without truncation.

**Functional Requirements:**

- Automatically chunk long prompts and concatenate embeddings
- No manual intervention required—just write longer prompts
- Works with SDXL and SD 1.5 models (CLIP-based)
- Not needed for Flux/Qwen (native 512-token support)

---

### 4.2 Prompt Weighting Syntax

**Capability:** Emphasize or de-emphasize specific concepts in prompts.

**Functional Requirements:**

- Support `(word:weight)` syntax where weight > 1.0 increases emphasis
- Example: `(beautiful:1.3)` for stronger emphasis
- Example: `(blur:0.5)` to reduce unwanted artifacts
- Handle SDXL dual text encoders properly
- Handle pooled embeddings for SDXL

---

## 5. CivitAI Integration

### 5.1 LoRA Auto-Download

**Capability:** Automatically download LoRA files from CivitAI using AIR URN identifiers.

**Functional Requirements:**

- Parse AIR URN format: `urn:air:{ecosystem}:{type}:civitai:{modelId}@{versionId}`
- Download LoRA file via CivitAI API with authentication
- Stream download with atomic file operations (temp file → rename)
- Report download progress and file size
- Requires `CIVITAI_API_KEY` environment variable

---

### 5.2 Metadata Extraction

**Capability:** Automatically populate LoRA configuration from CivitAI metadata.

**Functional Requirements:**

- Fetch model version metadata from CivitAI API
- Extract and map fields:
  - `trainedWords` → prompt trigger words
  - `baseModel` → base architecture (SD 1.5, SDXL, Flux)
  - `cfgScale` from example images → guidance_scale recommendation
  - `negativePrompt` from example images → negative prompt suffix
  - `description` → notes field
  - Download/rating stats → notes field
- Map CivitAI base model names to internal architecture codes

**CivitAI Base Model Mapping:**

| CivitAI baseModel | Internal Architecture |
|-------------------|----------------------|
| SD 1.5, SD 2.1 | `sd15` |
| SDXL 1.0, SDXL 0.9, SDXL Turbo, Pony | `sdxl` |
| Flux.1 D, Flux.1 S | `flux1` |

---

## 6. Configuration Management

### 6.1 Model Configuration Schema

**Capability:** Define model behavior and constraints via JSON configuration.

**Model Configuration Fields:**

| Field | Description | Required |
|-------|-------------|----------|
| `slug` | Unique identifier | Yes |
| `label` | Display name | Yes |
| `path` | HuggingFace ID or local path | Yes |
| `pipeline` | Diffusers pipeline class name | Yes |
| `base_architecture` | Architecture family | Yes |
| `settings.steps` | Default inference steps | Yes |
| `settings.guidance_scale` | Default CFG scale | Yes |
| `settings.default_width` | Default output width | Yes |
| `settings.default_height` | Default output height | Yes |
| `settings.max_pixels` | Maximum resolution (width × height) | Yes |
| `settings.dtype` | Precision (float16, bfloat16) | Yes |
| `settings.supports_negative_prompt` | Whether model uses negative prompts | Yes |
| `settings.token_window` | Context window size (77 or 512) | Yes |
| `settings.vram_usage` | Estimated VRAM in MB | Yes |
| `settings.scheduler` | Noise scheduler class name | No |
| `settings.force_default_guidance` | Ignore user CFG override | No |
| `settings.max_sequence_length` | Flux/Qwen context length | No |
| `settings.use_sequential_cpu_offload` | Use sequential vs model offload | No |

---

### 6.2 Preset Loading

**Capability:** Load all model and LoRA configurations from a single JSON file.

**Functional Requirements:**

- Load and validate `data/presets.json`
- Provide access to model configs by slug or label
- Provide access to LoRA configs filtered by model compatibility
- Resolve model paths (HuggingFace ID vs local file)
- Resolve LoRA paths relative to `base_model_path`
- Generate UI dropdown choices for models and LoRAs

---

### 6.3 Path Resolution

**Capability:** Support both HuggingFace Hub models and local `.safetensors` files transparently.

**Functional Requirements:**

- **HuggingFace:** paths starting with `Huggingface:` or containing `/` without `.safetensors` → load via `from_pretrained()`
- **Local:** paths ending in `.safetensors` → resolve relative to `base_model_path`, load via `from_single_file()`
- Strip `Huggingface:` prefix when loading from Hub

---

## 7. Model Preloading

### 7.1 Bulk Preload

**Capability:** Pre-download all models to HuggingFace cache for offline use.

**Functional Requirements:**

- Iterate through all models in presets
- Download and cache each model
- Report progress for each stage
- Continue with next model on error
- Report final summary

---

### 7.2 Selective Preload

**Capability:** Download a specific model by slug.

**Functional Requirements:**

- Accept model slug as argument
- Validate slug exists in presets
- Download and cache the specified model
- List available slugs if invalid slug provided

---

## 8. CLI Interfaces

### 8.1 Prompt Enhancer CLI

```bash
# Rule-based (no dependencies)
python prompt_enhancer.py "a cat"
python prompt_enhancer.py "a cat" --style photography --creativity 0.9

# Local HuggingFace model
python prompt_enhancer.py "a cat" --use-hf
python prompt_enhancer.py "a cat" --use-hf --hf-model Qwen/Qwen2.5-7B-Instruct

# Anthropic API
python prompt_enhancer.py "a cat" --use-llm --api-key sk-xxx

# Batch processing
python prompt_enhancer.py --file prompts.txt --output enhanced.json

# With LoRA trigger words
python prompt_enhancer.py "unicorn" --style coloring-book --trigger-words "sketch, pen sketch"

# List recommended models
python prompt_enhancer.py --list-hf-models
```

---

### 8.2 Model Preloader CLI

```bash
# Preload all models
python preloader.py

# Preload specific model
python preloader.py --model zimageturbo
python preloader.py --model flux1_dev
```

---

## 9. Error Handling & Reliability

**Functional Requirements:**

- **Graceful fallback:** LLM prompt enhancement falls back to rule-based on failure
- **Atomic downloads:** CivitAI downloads use temp files to prevent corruption
- **Device mismatch prevention:** MPS VAE kept on device in float32
- **LoRA load/unload recovery:** Re-apply device fixes after LoRA operations
- **Memory management:** Clear GPU cache after each generation
- **Validation:** Check LoRA file existence before attempting load
- **Resolution validation:** Enforce `max_pixels` constraint per model

---

## 10. Supported Models

| Model | Slug | Type | Steps | CFG | Neg. Prompt | VRAM | Notes |
|-------|------|------|-------|-----|-------------|------|-------|
| DreamShaper XL Lightning | `dreamshaper_xl` | Distilled | 4 | 2.0 | No | 8 GB | Fast SDXL |
| Flux.1-dev | `flux1_dev` | Full | 28 | 3.5 | No | 24 GB | High quality |
| Juggernaut XL v9 | `juggernaut_xl` | Full | 30 | 7.0 | Yes | 8 GB | Photorealistic SDXL |
| Qwen-Image-2512 | `qwen_image` | Full | 50 | 4.5 | Yes | 24 GB | 8-bit quantization |
| Realistic Vision v5.1 | `realistic_vision` | Full | 30 | 5.0 | Yes | 4 GB | SD 1.5 photorealistic |
| SDXL Turbo | `sdxl_turbo` | Distilled | 4 | 0.0 (forced) | No | 6 GB | Fast SDXL |
| Z-Image Turbo | `zimageturbo` | Distilled | 9 | 0.0 (forced) | No | 8 GB | Fast generation |

**Scheduler Reference:**

| Model | Scheduler |
|-------|-----------|
| DreamShaper XL | DPMSolverMultistepScheduler |
| SDXL Turbo | EulerAncestralDiscreteScheduler |
| Flux.1-dev, Qwen-Image, Z-Image Turbo | FlowMatchEulerDiscreteScheduler |

---

## 11. Hardware Requirements

| Tier | VRAM | Supported Models |
|------|------|------------------|
| Entry | 4–6 GB | Realistic Vision (SD 1.5), SDXL Turbo |
| Mid | 8 GB | DreamShaper XL, Juggernaut XL, Z-Image Turbo |
| High | 24+ GB | Flux.1-dev, Qwen-Image-2512 |

**Notes:**
- All models support CPU offloading on CUDA for reduced VRAM usage (slower)
- Apple Silicon (MPS) requires unified memory; 16 GB recommended minimum
- CPU-only inference supported but significantly slower
