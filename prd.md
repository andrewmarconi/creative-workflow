# QueerChaos 2 - Implementation Specification

## Project Overview
A Python script for batch image generation using Flux2 diffusion models on Apple Silicon (M4 Mac with 48GB RAM). The script processes JSON input files containing multiple prompts and generates images with resume capability and progress tracking.

## Technical Stack

### Core Dependencies
- **HuggingFace Diffusers**: Model loading and image generation
- **PyTorch with MPS** or **MLX**: Optimized for Apple Silicon M4
- **tqdm**: Progress tracking
- Python 3.10+

### Models (HuggingFace)
- **Diffusion Model**: `flux2_dev_fp8mixed`
- **Text Encoder**: `mistral_3_small_flux2_bf16`
- **LoRA**: Optional, specified per batch in input JSON
  - Can be HuggingFace model ID (e.g., `fofr/flux-80s-cyberpunk`)
  - OR local file path to `.safetensors` file (e.g., `./models/my_lora.safetensors`)

### Environment Setup
- Use uv env rather than conda or venv.
- Calling python from terminal should use the uv environment.
- Install dependencies via 'uv add ...' command.

### Authentication
- HuggingFace CLI authentication assumed pre-configured on local machine
- Script should use cached credentials

## Input Specification

### Input File
- **Default Path**: `./input.json`
- **CLI Override**: `python generate.py path/to/custom.json`
- **Format**: JSON with the following schema:

```json
{
  "count": <integer>,           // Number of images to generate per prompt
  "lora": {                      // Optional LoRA configuration
    "name": "<string>",          // HuggingFace model ID OR local path to .safetensors file
    "prompt": "<string>"         // Text to append to each prompt
  },
  "prompts": {                   // Dictionary of prefix: prompt pairs
    "<file_prefix>": "<prompt_text>",
    "<file_prefix_2>": "<prompt_text_2>"
  },
  "output_dir": "<string>"      // Output directory path (relative or absolute)
}
```

### Input Validation
- Required fields: `count`, `prompts`, `output_dir`
- Optional fields: `lora`
- `count` must be positive integer
- `prompts` must be non-empty object
- `output_dir` will be created if it doesn't exist

## Processing Logic

### Generation Flow
1. **Load Input JSON**: Parse and validate schema
2. **Initialize Models**:
   - Load Flux2 diffusion model with fp8 mixed precision
   - Load Mistral 3 Small text encoder (bf16)
   - Load LoRA if specified:
     - Check if `lora.name` is a local file path (contains `.safetensors`)
     - If local: Load from file system
     - If not: Load from HuggingFace Hub using model ID
   - Use Apple Silicon optimizations (MPS backend or MLX)
3. **Check Checkpoint**: Load existing checkpoint from output_dir if present
4. **Process Each Prompt**:
   - For each prompt in `prompts` object:
     - Generate `count` images
     - Use random seed for each image (different seeds per image)
     - Append LoRA prompt if specified
     - Save as `{file_prefix}_{1..count}.jpg`
     - Update checkpoint after each successful image
     - Log errors for failed generations

### Generation Parameters (Best Practices for Flux2 Dev)
- **Resolution**: 1024x1024 pixels
- **Steps**: 28-50 (use 28 for speed, 50 for quality)
- **Guidance Scale**: 3.5 (Flux2 Dev recommended)
- **Scheduler**: FlowMatchEulerDiscreteScheduler (default for Flux)
- **Dtype**: fp8 for model, bf16 for text encoder
- **Negative Prompts**: Not supported by Flux2 (omit entirely)

### Seed Management
- Generate random seed for each image using `random.randint(0, 2**32 - 1)`
- Seeds are NOT included in filenames
- Seeds ARE saved in output metadata JSON

## Output Specification

### Output Files

#### 1. Generated Images
- **Format**: JPG
- **Quality**: 95 (high quality JPEG compression)
- **Resolution**: 1024x1024
- **Naming**: `{file_prefix}_{index}.jpg`
  - Example: `futuristic_cityscape_1.jpg`, `futuristic_cityscape_2.jpg`, etc.
  - Index starts at 1, zero-padded to 3 digits if count > 99

#### 2. Metadata File: `generation_metadata.json`
Located in `output_dir`, contains generation parameters for all images:

```json
{
  "batch_config": {
    "count": 5,
    "lora": {
      "name": "lora_model_name",
      "prompt": "lora specific text"
    }
  },
  "model_config": {
    "diffusion_model": "flux2_dev_fp8mixed",
    "text_encoder": "mistral_3_small_flux2_bf16",
    "steps": 28,
    "guidance_scale": 3.5,
    "scheduler": "FlowMatchEulerDiscreteScheduler"
  },
  "images": [
    {
      "filename": "cityscape_1.jpg",
      "prompt": "A futuristic cityscape at sunset, lora specific text",
      "seed": 1234567890,
      "timestamp": "2026-01-31T10:30:45Z",
      "status": "success"
    },
    {
      "filename": "cityscape_2.jpg",
      "prompt": "A futuristic cityscape at sunset, lora specific text",
      "seed": 9876543210,
      "timestamp": "2026-01-31T10:32:15Z",
      "status": "failed",
      "error": "CUDA out of memory"
    }
  ]
}
```

#### 3. Checkpoint File: `.checkpoint.json`
Located in `output_dir`, tracks completion status:

```json
{
  "completed_images": [
    "cityscape_1.jpg",
    "cityscape_2.jpg",
    "portrait_1.jpg"
  ],
  "last_updated": "2026-01-31T10:32:15Z",
  "total_expected": 10
}
```

## Resume Behavior

### Checkpoint Logic
1. On startup, check for `.checkpoint.json` in output_dir
2. If exists, load completed_images list
3. For each prompt/index combination:
   - Check if output file exists in completed_images list
   - If yes, skip generation (show in progress as "Skipped")
   - If no, generate image
4. Update checkpoint after each successful generation
5. This allows resuming after crashes, interruptions, or manual stops

### Force Regenerate
- Delete `.checkpoint.json` to regenerate all images
- Delete specific image files to regenerate just those

## Error Handling

### Error Categories
1. **Model Loading Errors**: Fatal, exit with error code 1
2. **Input Validation Errors**: Fatal, exit with error code 1
3. **Individual Generation Errors**: Non-fatal, log and continue
   - Out of memory
   - Invalid prompt
   - Timeout
   - Model inference failures

### Error Logging
- Console: Show error message with prompt prefix
- Metadata JSON: Add entry with `"status": "failed"` and `"error": "<message>"`
- Continue processing remaining images

### Progress Display
Use tqdm with:
- Total: `len(prompts) * count`
- Description: Current prompt prefix
- Postfix: Success/failure counts
- Update after each image completion or skip

Example:
```
Processing: 45%|████████████          | 9/20 [02:15<02:45, Success: 8, Failed: 1, Skipped: 0]
```

## Performance Optimization

### Apple Silicon (M4) Specific
1. **Backend Selection**:
   - First choice: MLX if diffusers supports it
   - Fallback: PyTorch with MPS backend
   - Enable `torch.mps.set_per_process_memory_fraction(0.9)` for memory management

2. **Memory Management**:
   - Use `torch.mps.empty_cache()` between generations if using PyTorch
   - Process prompts sequentially (no parallel batching)
   - Load models once, reuse for all generations
   - Use fp8 quantization for diffusion model to save memory

3. **Model Loading**:
   - Load models at startup (not per-image)
   - Use `low_cpu_mem_usage=True` when loading
   - Cache models in HuggingFace cache directory

## Command-Line Interface

### Usage
```bash
python generate.py [input_file]
```

### Arguments
- `input_file` (optional): Path to JSON input file
  - Default: `./input.json`
  - Example: `python generate.py configs/batch1.json`

### Exit Codes
- `0`: Success (all images generated or skipped)
- `1`: Fatal error (model loading, invalid input)
- `2`: Partial success (some images failed, but at least one succeeded)

## File Structure

```
QueerChaos-2/
├── generate.py              # Main script
├── requirements.txt         # Python dependencies
├── input.json              # Default input file
├── README.md               # Usage instructions
└── outputs/                # Example output directory
    ├── .checkpoint.json    # Resume checkpoint
    ├── generation_metadata.json  # Complete metadata
    ├── prefix1_001.jpg
    ├── prefix1_002.jpg
    └── prefix2_001.jpg
```

## Implementation Checklist

### Phase 1: Setup & Model Loading
- [ ] Create Python script with CLI argument parsing
- [ ] Implement JSON schema validation
- [ ] Load Flux2 diffusion model with fp8 optimization
- [ ] Load Mistral 3 text encoder with bf16
- [ ] Implement LoRA loading (conditional)
- [ ] Configure Apple Silicon backend (MPS/MLX)

### Phase 2: Core Generation
- [ ] Implement prompt processing loop
- [ ] Random seed generation per image
- [ ] Image generation with best-practice parameters
- [ ] JPG saving with correct naming convention
- [ ] LoRA prompt appending logic

### Phase 3: Progress & Metadata
- [ ] tqdm progress bar with status counts
- [ ] Metadata JSON generation
- [ ] Timestamp and seed tracking
- [ ] Error status recording

### Phase 4: Resume & Error Handling
- [ ] Checkpoint file creation/loading
- [ ] Skip logic for completed images
- [ ] Error catching for individual generations
- [ ] Graceful continuation after failures

### Phase 5: Testing
- [ ] Test with single prompt
- [ ] Test with multiple prompts
- [ ] Test with LoRA
- [ ] Test without LoRA
- [ ] Test resume functionality
- [ ] Test error handling (invalid prompts)
- [ ] Verify memory usage on M4 Mac

## Example Usage

### Example 1: With HuggingFace LoRA

#### Input File: `input.json`
```json
{
  "count": 3,
  "lora": {
    "name": "fofr/flux-80s-cyberpunk",
    "prompt": "in 80s cyberpunk style"
  },
  "prompts": {
    "cityscape": "A futuristic cityscape at sunset, vibrant colors, high detail",
    "portrait": "Portrait of a cyberpunk hacker, neon lighting, detailed face",
    "vehicle": "Retro flying car in a neon city, raining, reflections"
  },
  "output_dir": "./outputs/cyberpunk_batch"
}
```

#### Command
```bash
python generate.py input.json
```

#### Expected Output
```
Loading models...
✓ Flux2 Dev (fp8) loaded
✓ Mistral 3 Small (bf16) loaded
✓ LoRA loaded: fofr/flux-80s-cyberpunk

Processing prompts: 100%|████████████| 9/9 [08:30<00:00, Success: 9, Failed: 0, Skipped: 0]

Generated 9 images in ./outputs/cyberpunk_batch/
Metadata saved to ./outputs/cyberpunk_batch/generation_metadata.json
```

#### Output Files
```
outputs/cyberpunk_batch/
├── .checkpoint.json
├── generation_metadata.json
├── cityscape_001.jpg
├── cityscape_002.jpg
├── cityscape_003.jpg
├── portrait_001.jpg
├── portrait_002.jpg
├── portrait_003.jpg
├── vehicle_001.jpg
├── vehicle_002.jpg
└── vehicle_003.jpg
```

### Example 2: With Local LoRA File

#### Input File: `input_local_lora.json`
```json
{
  "count": 2,
  "lora": {
    "name": "./models/custom_style.safetensors",
    "prompt": "in custom artistic style"
  },
  "prompts": {
    "landscape": "A serene mountain landscape with aurora borealis",
    "abstract": "Abstract geometric patterns with vibrant gradients"
  },
  "output_dir": "./outputs/custom_style_batch"
}
```

#### Command
```bash
python generate.py input_local_lora.json
```

#### Expected Output
```
Loading models...
✓ Flux2 Dev (fp8) loaded
✓ Mistral 3 Small (bf16) loaded
✓ LoRA loaded from: ./models/custom_style.safetensors

Processing prompts: 100%|████████████| 4/4 [04:15<00:00, Success: 4, Failed: 0, Skipped: 0]

Generated 4 images in ./outputs/custom_style_batch/
Metadata saved to ./outputs/custom_style_batch/generation_metadata.json
```

### Example 3: Without LoRA

#### Input File: `input_no_lora.json`
```json
{
  "count": 1,
  "prompts": {
    "simple_test": "A beautiful sunset over the ocean"
  },
  "output_dir": "./outputs/test"
}
```

#### Command
```bash
python generate.py input_no_lora.json
```

#### Expected Output
```
Loading models...
✓ Flux2 Dev (fp8) loaded
✓ Mistral 3 Small (bf16) loaded

Processing prompts: 100%|████████████| 1/1 [01:05<00:00, Success: 1, Failed: 0, Skipped: 0]

Generated 1 image in ./outputs/test/
Metadata saved to ./outputs/test/generation_metadata.json
```

## Notes for Implementation

1. **HuggingFace Model IDs**: Verify exact model IDs on HuggingFace Hub before implementation
2. **LoRA Loading**:
   - Detect local files by checking if path ends with `.safetensors` or exists on filesystem
   - For local files: validate file exists and is readable before attempting to load
   - For HuggingFace IDs: use standard Hub loading with proper error handling
   - Ensure LoRA models are compatible with Flux2 Dev architecture
3. **Memory Monitoring**: Log memory usage to help debug OOM issues
4. **Torch Compile**: Consider using `torch.compile()` for faster inference (PyTorch 2.0+)
5. **Graceful Shutdown**: Handle SIGINT (Ctrl+C) by saving checkpoint before exit
6. **Verbose Mode**: Consider adding `--verbose` flag for detailed logging (future enhancement)
