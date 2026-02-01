# ZImageTurbo Setup Guide

This guide explains how to configure and use the ZImageTurbo version of the image generator.

## Files

- **generate_zimageturbo.py** - Main script for ZImageTurbo
- **input_zimageturbo.json** - Sample input file

## Configuration Steps

### 1. Find the Correct Model ID

Visit HuggingFace and find the ZImageTurbo model. Update in `generate_zimageturbo.py`:

```python
class Config:
    MODEL_ID = "your-org/zimageturbo-model-name"  # Update this
```

### 2. Verify Generation Parameters

Turbo models typically use different parameters than standard models. Common settings:

```python
STEPS = 1-4           # Turbo models are fast
GUIDANCE_SCALE = 0.0  # Often don't use guidance
RESOLUTION = 512-1024 # Check model documentation
```

**TODO: Research ZImageTurbo's recommended parameters and update the Config class.**

### 3. Check Pipeline Class

The script uses `StableDiffusionXLPipeline` as a starting point (to avoid dependency issues with `AutoPipeline`).

**Common pipeline classes for turbo models:**
- `StableDiffusionXLPipeline` - SDXL-based turbo models
- `StableDiffusionPipeline` - SD 1.5-based turbo models
- `KandinskyPipeline` - Kandinsky-based models

**To change the pipeline:**

```python
from diffusers import YourPipelineClass

# In load_models():
pipeline = YourPipelineClass.from_pretrained(...)
```

**Note:** We avoid `AutoPipelineForText2Image` due to transformers 5.x compatibility issues.

### 4. Verify Scheduler

Turbo models often use specific schedulers. Current default: `EulerAncestralDiscreteScheduler`

Common alternatives:
- `EulerDiscreteScheduler`
- `DDIMScheduler`
- `PNDMScheduler`

Check ZImageTurbo documentation for the recommended scheduler.

### 5. Test Memory Usage

ZImageTurbo may have different memory requirements:

- **If it's smaller than Flux**: May not need sequential CPU offload
- **If it's similar/larger**: Keep the current memory optimizations

To disable CPU offload (if not needed):

```python
# In load_models(), change:
pipeline.enable_sequential_cpu_offload(device=device)
# To:
pipeline = pipeline.to(device)
```

## Usage

```bash
# Run with default input
python generate_zimageturbo.py input_zimageturbo.json

# Or create custom input
python generate_zimageturbo.py my_config.json
```

## Input JSON Format

Same format as Flux2 version:

```json
{
  "count": 2,
  "lora": {
    "name": "optional-lora-model",
    "prompt": "style suffix"
  },
  "prompts": {
    "prefix1": "prompt text 1",
    "prefix2": "prompt text 2"
  },
  "output_dir": "./outputs/zimageturbo"
}
```

## Key Differences from Flux2

| Feature | Flux2 | ZImageTurbo | Notes |
|---------|-------|-------------|-------|
| Steps | 28-50 | 1-4 | Turbo is much faster |
| Guidance | 3.5 | 0.0 | Turbo often uses 0 |
| Scheduler | FlowMatch | EulerAncestral | Model-specific |
| Speed | ~30-60s | ~2-5s | Estimate - varies |
| Memory | ~34GB | TBD | Check model size |

## Checklist Before First Run

- [ ] Updated `MODEL_ID` with correct HuggingFace model
- [ ] Verified `STEPS` parameter (check model docs)
- [ ] Verified `GUIDANCE_SCALE` (check model docs)
- [ ] Verified `RESOLUTION` (check model docs)
- [ ] Checked if correct pipeline class
- [ ] Checked if correct scheduler
- [ ] Tested memory requirements
- [ ] Created test input file
- [ ] Have HuggingFace authentication set up

## Troubleshooting

### Model Not Found
```
✗ Failed to load ZImageTurbo pipeline: ...
```
**Solution**: Verify the MODEL_ID is correct on HuggingFace

### Out of Memory
```
✗ MPS backend out of memory
```
**Solution**: Enable sequential CPU offload (should already be enabled)

### Wrong Parameters
```
Images look wrong or errors during generation
```
**Solution**: Check model documentation for recommended steps/guidance

## Resources

- **ZImageTurbo Model Card**: [Update with actual URL]
- **Diffusers Documentation**: https://huggingface.co/docs/diffusers
- **Scheduler Guide**: https://huggingface.co/docs/diffusers/api/schedulers/overview

## Testing

Use the same test files from `tests/` directory:

```bash
python generate_zimageturbo.py tests/test_single_prompt.json
```

Just update the output_dir in the test file to avoid conflicts.

## Notes

- This script maintains the same features as Flux2 version:
  - ✅ Checkpoint/resume capability
  - ✅ Progress tracking
  - ✅ Metadata generation
  - ✅ LoRA support
  - ✅ Error handling
  - ✅ Apple Silicon optimization

- The main differences are model-specific configurations
- All functionality should work the same way
