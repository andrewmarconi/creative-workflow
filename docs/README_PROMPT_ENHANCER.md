# Prompt Enhancement System for QueerChaos 2

A complete prompt enhancement toolkit specifically designed for diffusion models, with specialized support for coloring book generation using your sketch LoRA.

## 📁 Files Created

### Core Scripts
- **[prompt_enhancer.py](prompt_enhancer.py)** - Main enhancement engine
  - Rule-based enhancement (fast, no API needed)
  - Optional LLM enhancement (requires Anthropic API)
  - Supports multiple styles including coloring-book mode
  - LoRA trigger word integration

- **[coloring_book.py](coloring_book.py)** - Quick helper for coloring books
  - Automatically uses coloring-book style
  - Pre-configured with your LoRA trigger words
  - Simplifies command-line usage

### Documentation
- **[PROMPT_ENHANCER_GUIDE.md](PROMPT_ENHANCER_GUIDE.md)** - Complete guide for general usage
- **[COLORING_BOOK_GUIDE.md](COLORING_BOOK_GUIDE.md)** - Specialized guide for coloring book pages
- **[README_PROMPT_ENHANCER.md](README_PROMPT_ENHANCER.md)** - This file

### Example Prompt Files
- **[example_prompts.txt](example_prompts.txt)** - General image prompts
- **[coloring_book_prompts.txt](coloring_book_prompts.txt)** - Coloring book specific ideas

## 🚀 Quick Start

### For Coloring Book Pages (Recommended for Your Use Case)

```bash
# Single prompt
python coloring_book.py "a unicorn in a forest"

# Batch process your ideas
python coloring_book.py --file coloring_book_prompts.txt

# Save to JSON for later
python coloring_book.py --file coloring_book_prompts.txt --output enhanced.json

# Show negative prompts
python coloring_book.py "a dragon" --show-negative
```

### For General Image Generation

```bash
# Single prompt
python prompt_enhancer.py "a cat sitting on a windowsill"

# Choose style
python prompt_enhancer.py "a sunset" --style photography

# Adjust creativity
python prompt_enhancer.py "a dragon" --style cinematic --creativity 0.9

# Batch process
python prompt_enhancer.py --file example_prompts.txt --output enhanced.json
```

## 🎨 Coloring Book Workflow

Your LoRA trigger words: **"sketch, rough sketch, pen sketch"**

### Method 1: Using the Helper Script (Easiest)

```bash
# 1. Create or edit coloring_book_prompts.txt
# 2. Run the helper
python coloring_book.py --file coloring_book_prompts.txt --output ready.json

# 3. Open ready.json and copy prompts to QueerChaos 2 UI
```

### Method 2: Direct Usage

```bash
python prompt_enhancer.py "a butterfly" \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --show-negative
```

## 🎯 What Makes Coloring Book Mode Special?

### Adds Line Art Enhancements
- "clean lines", "clear outlines", "bold outlines"
- "simple shapes", "well-defined edges"
- "black and white", "no shading"
- "easy to color", "distinct sections"

### Provides Specialized Negative Prompts
- Excludes: colors, shading, gradients, textures
- Prevents: complex details, photorealism
- Ensures: clean line art suitable for coloring

### Subject-Aware Enhancement
- **Animals**: "simple shapes, easy-to-color sections"
- **Flowers**: "clear petals and leaves, distinct shapes"
- **People**: "simple facial features, clear outlines"
- **Patterns/Mandalas**: "symmetrical design, repeating patterns"
- **Buildings**: "simple architecture, clear windows and doors"

## 📊 Example Outputs

### Input
```
a unicorn
```

### Enhanced Output (Coloring Book Mode)
```
Prompt: sketch, rough sketch, pen sketch, a unicorn, no shading, coloring page style,
        simple shapes, well-defined shapes, professional coloring page

Negative: colored, shaded, shading, gradient, soft edges, blurry lines, unclear outlines,
          complex details, texture, photorealistic, detailed rendering, colored pencil,
          watercolor, painted, low quality, messy lines, incomplete outlines
```

## 🔧 Available Styles

| Style | Best For | Enhancements |
|-------|----------|--------------|
| `coloring-book` | Line art, coloring pages | Clean lines, simple shapes, no shading |
| `photography` | Realistic photos | DSLR, bokeh, lighting, composition |
| `artistic` | Digital art, illustrations | Concept art, artstation, gallery quality |
| `realistic` | Photorealistic images | Hyperrealistic, detailed, 8k |
| `cinematic` | Movie-like scenes | Dramatic lighting, film grain, epic |
| `auto` | Any (default) | Auto-detects from keywords |

## 🎚️ Creativity Levels

| Level | Effect | Best For |
|-------|--------|----------|
| 0.3-0.5 | Conservative | Simple subjects, minimal enhancement |
| 0.6-0.7 | Balanced (default) | Most use cases |
| 0.8-0.9 | Creative | Complex scenes, artistic images |

For coloring books, **0.6-0.8 is recommended**.

## 💡 Integration with QueerChaos 2

### With Your Models

**Z-Image Turbo** (9 steps, guidance 0.0)
- Load sketch LoRA
- Use enhanced prompt
- Negative prompts ignored (but include anyway)

**Qwen-Image-2512** (50 steps, guidance 4.5)
- Load sketch LoRA
- Use enhanced prompt
- **Use negative prompts!** They work and improve quality ~15%

### Workflow in UI
1. Generate prompts with `coloring_book.py`
2. Load your sketch LoRA in QueerChaos 2
3. Copy enhanced prompt to prompt field
4. Copy negative prompt to negative prompt field (if model supports)
5. Generate!

## 📝 Creating Your Own Prompt Lists

Create a text file with one prompt per line:

```txt
# my_ideas.txt (lines starting with # are ignored)

a magical unicorn
a butterfly garden
a friendly dragon
a fairy castle
```

Then enhance:

```bash
python coloring_book.py --file my_ideas.txt --output my_enhanced.json
```

## 🤖 Advanced: LLM Enhancement

For more sophisticated prompts, use Claude API:

```bash
# Set your API key
export ANTHROPIC_API_KEY=your_key_here

# Use LLM mode
python prompt_enhancer.py "a unicorn" \
  --style coloring-book \
  --trigger-words "sketch, rough sketch, pen sketch" \
  --use-llm

# Install anthropic if needed
uv add anthropic
```

LLM mode provides:
- More creative, context-aware descriptions
- Better understanding of complex subjects
- Natural language prompt expansion

## 📚 Full Documentation

- **[COLORING_BOOK_GUIDE.md](COLORING_BOOK_GUIDE.md)** - Everything about coloring book mode
- **[PROMPT_ENHANCER_GUIDE.md](PROMPT_ENHANCER_GUIDE.md)** - Complete feature documentation

## 🔍 Command Reference

### Coloring Book Helper

```bash
python coloring_book.py PROMPT [OPTIONS]
python coloring_book.py --file FILE [OPTIONS]

Options:
  --creativity 0.0-1.0    # Creativity level (default: 0.7)
  --show-negative         # Display negative prompts
  --output FILE.json      # Save to JSON
  --json                  # JSON output to stdout
```

### Main Enhancer

```bash
python prompt_enhancer.py PROMPT [OPTIONS]
python prompt_enhancer.py --file FILE [OPTIONS]

Options:
  --style STYLE              # auto, coloring-book, photography, artistic, realistic, cinematic
  --creativity 0.0-1.0       # Enhancement level (default: 0.7)
  --trigger-words "WORDS"    # LoRA trigger words to prepend
  --use-llm                  # Use Claude API for enhancement
  --api-key KEY              # Anthropic API key
  --show-negative            # Show negative prompts
  --output FILE.json         # Save to JSON
  --json                     # JSON output
```

## 💪 Tips for Best Results

### For Coloring Books
✅ Use simple, clear subjects
✅ Stick to 0.6-0.8 creativity
✅ Always include trigger words
✅ Use specialized negative prompts

❌ Avoid complex realistic scenes
❌ Don't use creativity > 0.9
❌ Don't forget the negative prompts

### For General Images
✅ Start with simple prompts
✅ Let auto-detection choose style
✅ Experiment with creativity levels
✅ Use LLM mode for complex subjects

## 🛠️ Customization

Edit `prompt_enhancer.py` to add your own:

- Quality tags (line 26)
- Style descriptors (line 31)
- Technical enhancements (line 54)
- Negative prompt defaults (line 60)
- Coloring book negatives (line 68)

## ❓ Troubleshooting

**coloring_book.py not working?**
- Make sure you're in the same directory as prompt_enhancer.py

**LoRA not activating?**
- Verify trigger words are at the START of the prompt
- Check LoRA is loaded in the UI

**Too many/few enhancements?**
- Adjust `--creativity` value
- Edit the style descriptors in the script

**Want different trigger words?**
- Edit line 10 in coloring_book.py
- Or use prompt_enhancer.py directly with `--trigger-words`

## 🎉 You're Ready!

Start generating amazing coloring book pages:

```bash
python coloring_book.py "a magical unicorn in an enchanted forest"
```

Then copy the enhanced prompt to QueerChaos 2 and generate!
