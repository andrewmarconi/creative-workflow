# HuggingFace Prompt Enhancer Setup Guide

## Installation

Install the required dependencies using `uv`:

```bash
# Core dependencies (required)
uv add transformers torch accelerate

# Optional: For download progress bars (recommended)
uv add tqdm
```

**What gets installed:**
- `transformers`: HuggingFace model loading
- `torch`: PyTorch with MPS support for Apple Silicon
- `accelerate`: Efficient model loading
- `tqdm`: (Optional) Progress bars during model download

## Quick Start

### 1. List Recommended Models
```bash
python prompt_enhancer.py --list-hf-models
```

### 2. Basic Usage (with default Qwen model)
```bash
python prompt_enhancer.py "a cat on a windowsill" --use-hf
```

**What you'll see:**
```
============================================================
Loading HuggingFace Model: Qwen/Qwen2.5-3B-Instruct
============================================================
✓ Device: Apple Silicon (MPS)

[1/3] Loading tokenizer...
✓ Tokenizer loaded

[2/3] Loading model weights...
      (First run: downloading from HuggingFace)
      (This may take 1-5 minutes depending on model size)
      (Download progress bars enabled via tqdm)
✓ Model weights loaded

[3/3] Moving model to device...
✓ Model ready on mps

============================================================
✓ Model loaded successfully!
============================================================

→ Formatting prompt for model...
→ Tokenizing input...
→ Generating enhanced prompt...
  (Using mps, creativity=0.7, max_tokens=512)
✓ Generation complete (3.2s)
→ Decoding response...

Original: a cat on a windowsill

Enhanced:
masterpiece, best quality, a cat on a windowsill, detailed facial features...
```

### 3. Use a Specific Model
```bash
# Flux-specialized model
python prompt_enhancer.py "a cat" --use-hf --hf-model gokaygokay/Flux-Prompt-Enhance

# Phi-3.5 (lightweight)
python prompt_enhancer.py "a cat" --use-hf --hf-model microsoft/Phi-3.5-mini-instruct

# Qwen 7B (higher quality)
python prompt_enhancer.py "a cat" --use-hf --hf-model Qwen/Qwen2.5-7B-Instruct
```

## Recommended Models

### 1. **Qwen/Qwen2.5-3B-Instruct** (DEFAULT)
- **Best for**: General use, matches your Qwen-Image ecosystem
- **Size**: 3B parameters (~6GB disk, ~3GB RAM in bfloat16)
- **Speed**: Fast on M4 Mac
- **Quality**: Excellent balance

### 2. **gokaygokay/Flux-Prompt-Enhance**
- **Best for**: Specialized Flux/Stable Diffusion enhancement
- **Size**: ~8B parameters (~16GB disk, ~8GB RAM)
- **Speed**: Moderate on M4 Mac
- **Quality**: Purpose-built for diffusion models

### 3. **microsoft/Phi-3.5-mini-instruct**
- **Best for**: Maximum speed, minimal memory
- **Size**: 3.8B parameters (~7.6GB disk, ~3.8GB RAM)
- **Speed**: Fastest option
- **Quality**: Very good for size

### 4. **Qwen/Qwen2.5-7B-Instruct**
- **Best for**: Highest quality enhancements
- **Size**: 7B parameters (~14GB disk, ~7GB RAM)
- **Speed**: Slower but still good on 48GB Mac
- **Quality**: Best creative expansions

## Advanced Usage

### With Style and Creativity Control
```bash
python prompt_enhancer.py "a dragon" --use-hf \
  --style cinematic \
  --creativity 0.9
```

### With LoRA Trigger Words
```bash
python prompt_enhancer.py "a unicorn" --use-hf \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch"
```

### Batch Processing from File
```bash
python prompt_enhancer.py --file prompts.txt --use-hf --output enhanced.json
```

### Show Negative Prompts
```bash
python prompt_enhancer.py "a cat" --use-hf --show-negative
```

## Apple Silicon Optimization

The `HFPromptEnhancer` is optimized for M4 Mac with:

- **MPS Backend**: Automatic detection and use of Apple Metal Performance Shaders
- **bfloat16 Precision**: Memory-efficient 16-bit floating point
- **Memory Management**: `torch.mps.empty_cache()` after each generation
- **Low CPU Memory**: `low_cpu_mem_usage=True` for efficient loading

## Performance Notes

**First Run**:
- Downloads model from HuggingFace Hub (~6-16GB depending on model)
- Cached in `~/.cache/huggingface/` for future use
- Initial load takes 10-30 seconds

**Subsequent Runs**:
- Loads from local cache (5-15 seconds)
- Generation: 2-10 seconds per prompt (depending on model size)

## Comparison of Methods

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Rule-based** | Instant, no dependencies, deterministic | Less creative, templated | Quick testing, consistent output |
| **HuggingFace** | Offline, free, customizable, MPS-optimized | Initial download, slower | Production use, custom models |
| **Anthropic API** | Highest quality, fastest generation | Requires API key, costs money, needs internet | Best quality, cloud-based |

## Troubleshooting

### "transformers not installed"
```bash
uv add transformers torch accelerate
```

### Out of Memory on MPS
Try a smaller model:
```bash
python prompt_enhancer.py "prompt" --use-hf --hf-model microsoft/Phi-3.5-mini-instruct
```

### Model Download Fails
Check your HuggingFace authentication:
```bash
huggingface-cli login
```

### Slow Generation
- First run downloads model (one-time)
- Use smaller model (Phi-3.5 or Qwen-3B)
- Enable MPS acceleration (automatic on Mac)

### Appears Frozen or Stuck?

**During first download:**
- Large models (3-8GB) take time to download
- Install `tqdm` for progress bars: `uv add tqdm`
- Progress is shown in terminal if tqdm is installed
- Check network activity to confirm download is happening

**During "Loading model weights...":**
- This step can take 30-60 seconds for large models
- The model is being loaded into memory and converted to bfloat16
- Watch for CPU/memory usage - it should be actively working
- No progress bar here, but status messages show progress

**During "Generating enhanced prompt...":**
- Shows generation time and device being used
- First generation is slower (model warmup)
- Typical times: 2-10 seconds depending on model size
- If stuck >30 seconds, press Ctrl+C and try a smaller model

**How to tell if it's actually working:**
- Check Activity Monitor (Mac) - Python should be using CPU/GPU
- Terminal shows step-by-step status updates
- Each step shows a ✓ when complete
- Times are shown: "Generation complete (3.2s)"

## Integration with Main App

To integrate with `main.py` for automatic prompt enhancement:

```python
from prompt_enhancer import HFPromptEnhancer

# Initialize once (reuse for all prompts)
enhancer = HFPromptEnhancer(
    model_id="Qwen/Qwen2.5-3B-Instruct",
    style="auto",
    creativity=0.7
)

# Use in generation
result = enhancer.enhance_prompt(simple_prompt)
enhanced = result['enhanced_prompt']
negative = result['negative_prompt']
```

## Examples

### Photography Style
```bash
$ python prompt_enhancer.py "a woman in a cafe" --use-hf --style photography

Original: a woman in a cafe

Enhanced:
masterpiece, best quality, a woman in a cafe, detailed facial features, expressive eyes,
professional photography, sharp focus, bokeh, golden hour lighting, studio lighting,
intricate details, perfect composition, balanced colors, high contrast
```

### Coloring Book Style
```bash
$ python prompt_enhancer.py "a butterfly" --use-hf --style coloring-book

Original: a butterfly

Enhanced:
a butterfly, simple shapes, easy-to-color sections, line art, clean lines, clear outlines,
black and white, simple shapes, high quality line art, professional coloring page,
well-defined shapes
```

### With Flux-Specialized Model
```bash
$ python prompt_enhancer.py "a cyberpunk city" --use-hf \
  --hf-model gokaygokay/Flux-Prompt-Enhance \
  --style cinematic

[Enhanced output optimized specifically for Flux model...]
```
