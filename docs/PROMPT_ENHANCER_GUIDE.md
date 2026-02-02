# Prompt Enhancer Guide

## Quick Start

```bash
# Single prompt
python prompt_enhancer.py "a cat"

# From file
python prompt_enhancer.py --file example_prompts.txt

# With options
python prompt_enhancer.py "a cat" --style photography --creativity 0.9 --show-negative
```

## Enhancement Strategies

### Rule-Based Mode (Default)
Fast and free, uses research-backed quality tags and technical terms:
- **Quality tags**: "masterpiece", "highly detailed", "professional"
- **Technical terms**: "sharp focus", "intricate details", "balanced colors"
- **Style-specific**: Auto-detects photography/artistic/cinematic/realistic
- **Context-aware**: Adds relevant details based on subject (faces, landscapes, animals, etc.)

### LLM Mode (Advanced)
Uses Claude API for sophisticated, creative expansion:

```bash
# Set API key as environment variable
export ANTHROPIC_API_KEY=your_key_here
python prompt_enhancer.py "a cat" --use-llm

# Or pass directly
python prompt_enhancer.py "a cat" --use-llm --api-key your_key_here
```

**To install Anthropic SDK:**
```bash
uv add anthropic
```

## Style Options

- `auto` (default) - Detects best style from prompt keywords
- `photography` - DSLR, bokeh, studio lighting, rule of thirds
- `artistic` - Concept art, illustration, trending on artstation
- `realistic` - Photorealistic, hyperrealistic, 8k, natural colors
- `cinematic` - Movie still, dramatic lighting, film grain, depth of field

## Creativity Levels

- `0.3-0.5` - Conservative, fewer enhancements, focused on quality
- `0.7` (default) - Balanced, good mix of quality and detail
- `0.9-1.0` - Maximum creativity, many descriptive tags

## Output Formats

### Human-readable (default)
```
Original: a cat
Enhanced: highly detailed, professional, a cat, detailed fur...
```

### JSON
```bash
python prompt_enhancer.py "a cat" --json
```

### Save to file
```bash
python prompt_enhancer.py --file prompts.txt --output enhanced.json
```

## Integration with QueerChaos 2

The enhanced prompts work great with all models in this project:

### For Z-Image Turbo (9 steps, guidance 0.0)
- Use moderate creativity (0.6-0.7)
- Focus on visual details, not technical photography terms
- The model ignores negative prompts

### For Flux.1-dev (28 steps, guidance 3.5)
- Use higher creativity (0.8-0.9)
- Add artistic and composition details
- The model ignores negative prompts

### For Qwen-Image-2512 (50 steps, guidance 4.5)
- Use maximum creativity (0.9-1.0)
- **Use negative prompts!** They improve quality ~15%
- Add rich descriptive details

## Tips for Best Results

1. **Start simple** - Let the enhancer add details
   - Good: "a cat"
   - Avoid: "a super detailed professional photo of a cat with bokeh"

2. **Be specific about subject** - Helps auto-detection
   - "portrait of a woman" → photography style
   - "painting of a woman" → artistic style

3. **Batch processing** - Process multiple prompts at once
   ```bash
   python prompt_enhancer.py --file my_ideas.txt --output enhanced.json
   ```

4. **Experiment with creativity** - Higher isn't always better
   - Simple subjects: 0.6-0.7
   - Complex scenes: 0.8-0.9

5. **Use negative prompts selectively**
   - Only Qwen-Image-2512 supports them in this project
   - Always include for Qwen, skip for others

## Example Workflow

```bash
# 1. Create a file with simple ideas
cat > my_prompts.txt << EOF
a magical forest
cyberpunk street scene
serene mountain lake
EOF

# 2. Enhance them
python prompt_enhancer.py --file my_prompts.txt --show-negative

# 3. Copy enhanced prompts into main.py UI
# 4. For Qwen model, also paste the negative prompt
```

## Advanced: Custom Enhancement

Edit the script to add your own:
- Quality tags (line 20-24)
- Style descriptors (line 26-46)
- Technical terms (line 48-54)
- Negative prompt defaults (line 56-62)

## Troubleshooting

**"anthropic package not installed"** when using `--use-llm`:
```bash
uv add anthropic
```

**Prompts too long:**
- Reduce creativity to 0.5 or lower
- Use rule-based mode instead of LLM
- Edit quality tags to use fewer options

**Not enough variety:**
- Increase creativity to 0.9
- Try LLM mode for more creative expansions
- Add more style descriptors to the script
