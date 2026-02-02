# Coloring Book Prompt Enhancement Guide

This guide shows how to use the prompt enhancer specifically for creating coloring book pages with your LoRA.

## Your LoRA Trigger Words

Your LoRA is activated with: **"sketch, rough sketch, pen sketch"**

These words MUST appear in every prompt for the LoRA to work properly.

## Quick Start

```bash
# Single coloring book prompt
python prompt_enhancer.py "a unicorn" \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch"

# Batch process coloring book ideas
python prompt_enhancer.py --file coloring_book_prompts.txt \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --output enhanced_coloring.json
```

## What Coloring-Book Style Does

The coloring-book style is specifically designed for line art and adds:

### Positive Enhancements
- **Line art qualities**: "clean lines", "clear outlines", "bold outlines"
- **Simplicity**: "simple shapes", "well-defined edges", "distinct sections"
- **Printability**: "black and white", "printable quality", "professional coloring page"
- **Coloring-friendly**: "easy to color", "clear boundaries", "no shading"

### Negative Prompts (What to Avoid)
- **Colors**: "colored", "painted", "watercolor", "colored pencil"
- **Rendering**: "shaded", "shading", "gradient", "texture"
- **Complexity**: "photorealistic", "detailed rendering", "soft edges"
- **Quality issues**: "blurry lines", "messy lines", "unclear outlines"

## Example Transformations

### Simple → Enhanced

**Input:** `"a unicorn"`

**Output:**
```
sketch, rough sketch, pen sketch, a unicorn, no shading, coloring page style,
simple shapes, well-defined shapes, professional coloring page
```

**Negative:**
```
colored, shaded, shading, gradient, soft edges, blurry lines, unclear outlines,
complex details, texture, photorealistic, detailed rendering, colored pencil,
watercolor, painted, low quality, messy lines, incomplete outlines
```

### Subject-Specific Enhancements

**Animals:** `"a butterfly"` → adds "simple shapes, easy-to-color sections"

**Flowers:** `"a rose"` → adds "clear petals and leaves, distinct shapes"

**People:** `"a fairy princess"` → adds "simple facial features, clear outlines"

**Patterns:** `"mandala"` → adds "symmetrical design, repeating patterns"

**Buildings:** `"a castle"` → adds "simple architecture, clear windows and doors"

## Workflow for Coloring Books

### 1. Create Your Prompt List

Edit [coloring_book_prompts.txt](coloring_book_prompts.txt) or create your own:

```txt
a unicorn in a forest
a butterfly on a flower
a cute dragon
a magical castle
```

### 2. Enhance All Prompts

```bash
python prompt_enhancer.py --file coloring_book_prompts.txt \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --output my_enhanced.json
```

### 3. Use in QueerChaos 2

Open the generated JSON file and copy the enhanced prompts into the UI:

```json
{
  "prompts": [
    {
      "original": "a unicorn in a forest",
      "enhanced_prompt": "sketch, rough sketch, pen sketch, a unicorn in a forest, line art, ...",
      "negative_prompt": "colored, shaded, shading, gradient, ..."
    }
  ]
}
```

### 4. Generate Images

1. Load your sketch LoRA in the UI
2. Paste the `enhanced_prompt` into the prompt field
3. Paste the `negative_prompt` into the negative prompt field
4. Generate!

## Tips for Best Coloring Book Results

### Subject Selection
✓ **Good subjects:**
- Animals with clear shapes (unicorns, butterflies, cats, dragons)
- Flowers and plants (roses, sunflowers, trees)
- Fantasy characters (fairies, wizards, mermaids)
- Patterns and mandalas (geometric, floral, symmetrical)
- Simple objects (teacups, bicycles, houses)

✗ **Avoid:**
- Complex realistic scenes
- Subjects with fine textures (fur, grass)
- Abstract concepts
- Photographic subjects

### Creativity Settings

For coloring books, use **moderate creativity** (0.6-0.8):

```bash
# More conservative - simpler lines
python prompt_enhancer.py "a cat" --style coloring-book --creativity 0.6 ...

# More detailed - still line art but more elements
python prompt_enhancer.py "a cat" --style coloring-book --creativity 0.8 ...
```

**Don't go too high** - creativity >0.9 can add too many tags that might confuse the model.

### Auto-Detection

If you include keywords like "coloring" or "line art" in your prompt, the style will auto-detect:

```bash
# These will auto-detect as coloring-book style
python prompt_enhancer.py "coloring page of a cat" --trigger-words "sketch, rough sketch, pen sketch"
python prompt_enhancer.py "line art dragon" --trigger-words "sketch, rough sketch, pen sketch"
```

## Integration with Your Models

Your setup uses Z-Image Turbo primarily. Here's how to use the enhanced prompts:

### Z-Image Turbo Settings
- **Steps**: 9 (optimal for turbo)
- **Guidance**: 0.0 (turbo has internalized CFG)
- **LoRA**: Load your sketch LoRA
- **Negative Prompt**: Z-Image Turbo ignores negative prompts, but include them anyway for consistency

### Qwen-Image-2512 (If Using)
- **Steps**: 50
- **Guidance**: 4.5
- **LoRA**: Load your sketch LoRA
- **Negative Prompt**: **IMPORTANT** - Qwen DOES support negative prompts and they improve quality ~15%!

## Batch Generation Example

Generate multiple coloring pages at once:

```bash
# 1. Enhance prompts
python prompt_enhancer.py --file coloring_book_prompts.txt \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --output enhanced.json

# 2. View the results
cat enhanced.json

# 3. Copy prompts to a simple text file for easy access
python -c "
import json
data = json.load(open('enhanced.json'))
for p in data['prompts']:
    print('PROMPT:', p['enhanced_prompt'])
    print('NEGATIVE:', p['negative_prompt'])
    print('---')
" > ready_to_use.txt
```

## Advanced: Custom Enhancements

Want to add your own style descriptors? Edit [prompt_enhancer.py](prompt_enhancer.py):

Find the `STYLE_DESCRIPTORS` section (around line 31) and add to `"coloring-book"`:

```python
"coloring-book": [
    "line art", "clean lines", "clear outlines", "black and white",
    "simple shapes", "well-defined edges", "bold outlines",
    "coloring page style", "no shading", "flat design",
    "easy to color", "distinct sections",
    # Add your custom terms here:
    "thick outlines", "kid-friendly", "large areas"
]
```

## Troubleshooting

**Lines are too complex:**
- Reduce creativity to 0.5-0.6
- Add negative prompt: "intricate details, fine lines, complex patterns"

**Not enough detail:**
- Increase creativity to 0.8-0.9
- Try LLM mode for more sophisticated descriptions

**LoRA not activating:**
- Make sure trigger words are at the START of the prompt
- Check that `--trigger-words` is exactly: `"sketch, rough sketch, pen sketch"`
- Verify LoRA is loaded in the UI

**Generated images have color/shading:**
- Check that negative prompt is being used
- Increase LoRA strength in UI
- Make sure you're using coloring-book style

## Quick Reference

```bash
# Standard coloring book usage
python prompt_enhancer.py "SUBJECT" \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --show-negative

# Batch process
python prompt_enhancer.py --file my_prompts.txt \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --output enhanced.json

# With custom creativity
python prompt_enhancer.py "SUBJECT" \
  --style coloring-book \
  --creativity 0.8 \
  --trigger-words "sketch, rough sketch, pen sketch"
```

Happy coloring book creation! 🎨
