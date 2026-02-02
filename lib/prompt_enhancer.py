#!/usr/bin/env python3
"""
Prompt Enhancer for Diffusion Models

Expands simple text prompts into detailed, high-quality prompts optimized for
diffusion models. Supports both rule-based and LLM-based enhancement.

Usage:
    python prompt_enhancer.py "a cat"
    python prompt_enhancer.py --file prompts.txt
    python prompt_enhancer.py "a cat" --use-llm --api-key YOUR_KEY
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional
import random


class PromptEnhancer:
    """Enhances simple prompts for better diffusion model results."""

    # Quality and technical enhancement tags
    QUALITY_TAGS = [
        "masterpiece", "best quality", "high quality", "highly detailed",
        "professional", "award-winning", "stunning", "exceptional detail"
    ]

    STYLE_DESCRIPTORS = {
        "photography": [
            "professional photography", "DSLR", "sharp focus", "bokeh",
            "perfectly composed", "rule of thirds", "golden hour lighting",
            "studio lighting", "natural lighting", "cinematic lighting"
        ],
        "artistic": [
            "concept art", "digital art", "illustration", "artwork",
            "trending on artstation", "by renowned artist", "gallery quality",
            "fine art", "artistic composition"
        ],
        "realistic": [
            "photorealistic", "hyperrealistic", "lifelike", "realistic details",
            "accurate proportions", "natural colors", "true to life",
            "8k resolution", "ultra HD"
        ],
        "cinematic": [
            "cinematic", "movie still", "film grain", "wide angle",
            "dramatic lighting", "atmospheric", "moody", "epic composition",
            "depth of field"
        ],
        "coloring-book": [
            "line art", "clean lines", "clear outlines", "black and white",
            "simple shapes", "well-defined edges", "bold outlines",
            "coloring page style", "no shading", "flat design",
            "easy to color", "distinct sections"
        ]
    }

    TECHNICAL_ENHANCEMENTS = [
        "intricate details", "sharp focus", "crisp details", "perfect composition",
        "balanced colors", "rich colors", "vibrant", "dynamic range",
        "high contrast", "well-lit", "professional grade"
    ]

    NEGATIVE_PROMPT_DEFAULTS = [
        "blurry", "low quality", "worst quality", "low resolution",
        "jpeg artifacts", "compression artifacts", "distorted", "deformed",
        "ugly", "duplicate", "mutilated", "poorly drawn", "bad anatomy",
        "bad proportions", "watermark", "signature", "text"
    ]

    COLORING_BOOK_NEGATIVE_PROMPTS = [
        "colored", "shaded", "shading", "gradient", "soft edges", "blurry lines",
        "unclear outlines", "complex details", "texture", "photorealistic",
        "detailed rendering", "colored pencil", "watercolor", "painted",
        "low quality", "messy lines", "incomplete outlines", "bad anatomy",
        "poorly drawn", "distorted", "watermark", "signature", "text"
    ]

    def __init__(self, style: str = "auto", creativity: float = 0.7,
                 trigger_words: Optional[str] = None):
        """
        Initialize the prompt enhancer.

        Args:
            style: Enhancement style (photography, artistic, realistic, cinematic, coloring-book, auto)
            creativity: How creative to be with enhancements (0.0-1.0)
            trigger_words: Optional LoRA trigger words to always include at the start
        """
        self.style = style
        self.creativity = max(0.0, min(1.0, creativity))
        self.trigger_words = trigger_words

    def enhance_prompt(self, simple_prompt: str) -> dict:
        """
        Enhance a simple prompt with quality tags and detailed descriptions.

        Args:
            simple_prompt: The basic prompt to enhance

        Returns:
            dict with 'enhanced_prompt', 'negative_prompt', 'original'
        """
        simple_prompt = simple_prompt.strip()

        if not simple_prompt:
            return {
                "original": "",
                "enhanced_prompt": "",
                "negative_prompt": ""
            }

        # Auto-detect style from prompt
        style = self._detect_style(simple_prompt) if self.style == "auto" else self.style

        # Build enhanced prompt components
        components = []

        # Add trigger words first if provided
        if self.trigger_words:
            components.append(self.trigger_words)

        # For coloring book style, use different enhancement approach
        if style == "coloring-book":
            components.extend(self._enhance_coloring_book_prompt(simple_prompt))
        else:
            # Add quality tags (2-3 random ones based on creativity)
            num_quality = max(2, int(3 * self.creativity))
            quality_tags = random.sample(self.QUALITY_TAGS, min(num_quality, len(self.QUALITY_TAGS)))
            components.extend(quality_tags)

            # Add the core prompt
            core_prompt = self._enhance_core_prompt(simple_prompt)
            components.append(core_prompt)

            # Add style descriptors
            if style in self.STYLE_DESCRIPTORS:
                num_style = max(2, int(4 * self.creativity))
                style_tags = random.sample(
                    self.STYLE_DESCRIPTORS[style],
                    min(num_style, len(self.STYLE_DESCRIPTORS[style]))
                )
                components.extend(style_tags)

            # Add technical enhancements
            num_technical = max(2, int(4 * self.creativity))
            technical_tags = random.sample(
                self.TECHNICAL_ENHANCEMENTS,
                min(num_technical, len(self.TECHNICAL_ENHANCEMENTS))
            )
            components.extend(technical_tags)

        # Join components
        enhanced_prompt = ", ".join(components)

        # Build negative prompt (use coloring book specific for that style)
        if style == "coloring-book":
            negative_prompt = ", ".join(self.COLORING_BOOK_NEGATIVE_PROMPTS)
        else:
            negative_prompt = ", ".join(self.NEGATIVE_PROMPT_DEFAULTS)

        return {
            "original": simple_prompt,
            "enhanced_prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            "detected_style": style
        }

    def _enhance_coloring_book_prompt(self, prompt: str) -> List[str]:
        """
        Enhance prompt specifically for coloring book pages.
        Returns list of components (without trigger words - those are added separately).
        """
        components = []
        prompt_lower = prompt.lower()

        # Core subject with coloring book context
        core_prompt = self._enhance_core_prompt_coloring(prompt)
        components.append(core_prompt)

        # Add coloring book style descriptors
        num_style = max(3, int(5 * self.creativity))
        style_tags = random.sample(
            self.STYLE_DESCRIPTORS["coloring-book"],
            min(num_style, len(self.STYLE_DESCRIPTORS["coloring-book"]))
        )
        components.extend(style_tags)

        # Quality tags specific to line art
        coloring_quality = [
            "high quality line art", "professional coloring page",
            "well-defined shapes", "clear boundaries", "printable quality"
        ]
        num_quality = max(2, int(3 * self.creativity))
        components.extend(random.sample(coloring_quality, min(num_quality, len(coloring_quality))))

        return components

    def _enhance_core_prompt_coloring(self, prompt: str) -> str:
        """Add contextual details for coloring book style."""
        prompt_lower = prompt.lower()

        # Add simple, clear descriptors for coloring pages
        if any(word in prompt_lower for word in ["person", "woman", "man", "girl", "boy", "child"]):
            prompt += ", simple facial features, clear outlines"

        if any(word in prompt_lower for word in ["animal", "cat", "dog", "bird", "butterfly", "fish"]):
            prompt += ", simple shapes, easy-to-color sections"

        if any(word in prompt_lower for word in ["flower", "plant", "tree", "nature"]):
            prompt += ", clear petals and leaves, distinct shapes"

        if any(word in prompt_lower for word in ["mandala", "pattern", "geometric"]):
            prompt += ", symmetrical design, repeating patterns"

        if any(word in prompt_lower for word in ["building", "house", "castle", "city"]):
            prompt += ", simple architecture, clear windows and doors"

        return prompt

    def _detect_style(self, prompt: str) -> str:
        """Auto-detect the best style based on prompt keywords."""
        prompt_lower = prompt.lower()

        coloring_keywords = ["coloring", "coloring book", "coloring page", "line art"]
        photo_keywords = ["photo", "portrait", "selfie", "picture", "photograph"]
        art_keywords = ["painting", "drawing", "sketch", "illustration", "art"]
        cinematic_keywords = ["movie", "film", "scene", "cinematic", "dramatic"]

        if any(kw in prompt_lower for kw in coloring_keywords):
            return "coloring-book"
        elif any(kw in prompt_lower for kw in photo_keywords):
            return "photography"
        elif any(kw in prompt_lower for kw in art_keywords):
            return "artistic"
        elif any(kw in prompt_lower for kw in cinematic_keywords):
            return "cinematic"
        else:
            return "realistic"

    def _enhance_core_prompt(self, prompt: str) -> str:
        """Add contextual details to the core prompt."""
        prompt_lower = prompt.lower()

        # Add contextual enhancements based on subject
        if any(word in prompt_lower for word in ["person", "woman", "man", "girl", "boy", "portrait"]):
            prompt += ", detailed facial features, expressive eyes"

        if any(word in prompt_lower for word in ["landscape", "nature", "scenery", "outdoor"]):
            prompt += ", vast scenery, atmospheric perspective"

        if any(word in prompt_lower for word in ["animal", "cat", "dog", "bird", "wildlife"]):
            prompt += ", detailed fur/feathers, lifelike texture"

        if any(word in prompt_lower for word in ["building", "architecture", "city", "urban"]):
            prompt += ", architectural details, structural precision"

        return prompt


class HFPromptEnhancer(PromptEnhancer):
    """Enhanced version using local HuggingFace models (optimized for Apple Silicon)."""

    def __init__(self, model_id: str = "Qwen/Qwen2.5-3B-Instruct",
                 style: str = "auto", creativity: float = 0.7,
                 trigger_words: Optional[str] = None,
                 device: Optional[str] = None):
        """
        Initialize HuggingFace model-based enhancer.

        Args:
            model_id: HuggingFace model ID (e.g., "Qwen/Qwen2.5-3B-Instruct")
            style: Enhancement style
            creativity: Creativity level
            trigger_words: Optional LoRA trigger words
            device: Device to use ('cpu', 'mps', 'cuda', or None for auto-detect)
        """
        super().__init__(style, creativity, trigger_words)
        self.model_id = model_id
        self.model = None
        self.tokenizer = None
        self.device = device  # Will be set in _load_model if None
        self._load_model()

    def _load_model(self):
        """Load the HuggingFace model with MPS optimization for Apple Silicon."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
        except ImportError:
            print("Warning: transformers/torch not installed. Falling back to rule-based enhancement.")
            print("Install with: uv add transformers torch accelerate")
            return

        print(f"\n{'='*60}")
        print(f"Loading HuggingFace Model: {self.model_id}")
        print(f"{'='*60}")

        # Detect device (MPS for Apple Silicon, CUDA for NVIDIA, CPU fallback)
        if self.device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
                print("✓ Device: Apple Silicon (MPS)")
            elif torch.cuda.is_available():
                self.device = "cuda"
                print("✓ Device: CUDA (NVIDIA GPU)")
            else:
                self.device = "cpu"
                print("✓ Device: CPU (slower)")
        else:
            print(f"✓ Device: {self.device} (forced)")

        try:
            print("\n[1/3] Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            print("✓ Tokenizer loaded")

            print("\n[2/3] Loading model weights...")
            print("      (First run: downloading from HuggingFace)")
            print("      (This may take 1-5 minutes depending on model size)")

            # Check if tqdm is installed for download progress
            try:
                import tqdm
                print("      (Download progress bars enabled via tqdm)")
            except ImportError:
                print("      (Tip: Install tqdm for download progress: uv add tqdm)")

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=torch.bfloat16 if self.device != "cpu" else torch.float32,
                device_map=self.device,
                low_cpu_mem_usage=True
            )
            print("✓ Model weights loaded")

            print("\n[3/3] Moving model to device...")
            # Model is already on device via device_map, just confirm
            print(f"✓ Model ready on {self.device}")

            print(f"\n{'='*60}")
            print(f"✓ Model loaded successfully!")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n✗ Error loading model: {e}")
            print("✗ Falling back to rule-based enhancement.\n")
            self.model = None
            self.tokenizer = None

    def enhance_prompt(self, simple_prompt: str) -> dict:
        """Use local HuggingFace model to create a sophisticated enhanced prompt."""
        # Fallback if model didn't load
        if self.model is None or self.tokenizer is None:
            return super().enhance_prompt(simple_prompt)

        import torch

        # Build style-specific guidance
        style_guidance = ""
        if self.style == "coloring-book":
            style_guidance = """
Special instructions for coloring book style:
- Focus on LINE ART qualities: clean lines, clear outlines, bold boundaries
- Emphasize simplicity and clarity for easy coloring
- Avoid: shading, gradients, colors, textures, photorealism
- Include: simple shapes, well-defined sections, distinct areas
- Negative prompt should exclude: colored, shaded, gradient, soft edges, texture"""
        else:
            style_guidance = f"- Style preference: {self.style}"

        trigger_guidance = ""
        if self.trigger_words:
            trigger_guidance = f"""
IMPORTANT: The enhanced prompt MUST start with these exact trigger words: "{self.trigger_words}"
These are LoRA activation keywords and must appear at the beginning."""

        system_message = f"""You are an expert at writing prompts for diffusion models like Stable Diffusion, Flux, and similar image generators.

Your task is to take a simple prompt and expand it into a detailed, high-quality prompt that will produce excellent results.

Guidelines:
- Add specific details about composition, lighting, style, and quality
- Include technical photography/art terms when appropriate
- Make prompts vivid and descriptive
{style_guidance}
- Creativity level: {self.creativity}/1.0 (higher = more creative additions)
- Keep the core subject but add rich context
- Format as comma-separated tags/phrases
- DO NOT use conversational language, just descriptive tags
{trigger_guidance}

Also provide a negative prompt listing things to avoid (blur, low quality, artifacts, etc.)."""

        user_message = f"""Simple prompt: {simple_prompt}

Expand this into:
1. An enhanced prompt (comma-separated descriptive tags)
2. A negative prompt (comma-separated things to avoid)

Format your response as JSON:
{{"enhanced_prompt": "...", "negative_prompt": "..."}}"""

        # Format for chat models
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        try:
            print("→ Formatting prompt for model...")
            # Apply chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            print("→ Tokenizing input...")
            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)

            print("→ Generating enhanced prompt...")
            print(f"  (Using {self.device}, creativity={self.creativity}, max_tokens=512)")
            # Generate
            import time
            start_time = time.time()

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=self.creativity,
                    do_sample=True if self.creativity > 0 else False,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            generation_time = time.time() - start_time
            print(f"✓ Generation complete ({generation_time:.1f}s)")

            print("→ Decoding response...")
            # Decode
            response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)

            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Clear MPS cache if using Apple Silicon
                if self.device == "mps":
                    torch.mps.empty_cache()

                return {
                    "original": simple_prompt,
                    "enhanced_prompt": result.get("enhanced_prompt", ""),
                    "negative_prompt": result.get("negative_prompt", ""),
                    "method": "huggingface",
                    "model": self.model_id
                }
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"HuggingFace model enhancement failed: {e}. Falling back to rule-based.")
            return super().enhance_prompt(simple_prompt)


class LLMPromptEnhancer(PromptEnhancer):
    """Enhanced version using LLM API for more sophisticated expansions."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022",
                 style: str = "auto", creativity: float = 0.7,
                 trigger_words: Optional[str] = None):
        """
        Initialize LLM-based enhancer.

        Args:
            api_key: Anthropic API key
            model: Model to use for enhancement
            style: Enhancement style
            creativity: Creativity level
            trigger_words: Optional LoRA trigger words
        """
        super().__init__(style, creativity, trigger_words)
        self.api_key = api_key
        self.model = model

    def enhance_prompt(self, simple_prompt: str) -> dict:
        """Use LLM to create a sophisticated enhanced prompt."""
        try:
            import anthropic
        except ImportError:
            print("Warning: anthropic package not installed. Falling back to rule-based enhancement.")
            print("Install with: uv add anthropic")
            return super().enhance_prompt(simple_prompt)

        client = anthropic.Anthropic(api_key=self.api_key)

        # Build style-specific guidance
        style_guidance = ""
        if self.style == "coloring-book":
            style_guidance = """
Special instructions for coloring book style:
- Focus on LINE ART qualities: clean lines, clear outlines, bold boundaries
- Emphasize simplicity and clarity for easy coloring
- Avoid: shading, gradients, colors, textures, photorealism
- Include: simple shapes, well-defined sections, distinct areas
- Negative prompt should exclude: colored, shaded, gradient, soft edges, texture"""
        else:
            style_guidance = f"- Style preference: {self.style}"

        trigger_guidance = ""
        if self.trigger_words:
            trigger_guidance = f"""
IMPORTANT: The enhanced prompt MUST start with these exact trigger words: "{self.trigger_words}"
These are LoRA activation keywords and must appear at the beginning."""

        system_prompt = f"""You are an expert at writing prompts for diffusion models like Stable Diffusion, Flux, and similar image generators.

Your task is to take a simple prompt and expand it into a detailed, high-quality prompt that will produce excellent results.

Guidelines:
- Add specific details about composition, lighting, style, and quality
- Include technical photography/art terms when appropriate
- Make prompts vivid and descriptive
{style_guidance}
- Creativity level: {self.creativity}/1.0 (higher = more creative additions)
- Keep the core subject but add rich context
- Format as comma-separated tags/phrases
- DO NOT use conversational language, just descriptive tags
{trigger_guidance}

Also provide a negative prompt listing things to avoid (blur, low quality, artifacts, etc.)."""

        user_message = f"""Simple prompt: {simple_prompt}

Expand this into:
1. An enhanced prompt (comma-separated descriptive tags)
2. A negative prompt (comma-separated things to avoid)

Format your response as JSON:
{{"enhanced_prompt": "...", "negative_prompt": "..."}}"""

        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=self.creativity,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )

            response_text = message.content[0].text

            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "original": simple_prompt,
                    "enhanced_prompt": result.get("enhanced_prompt", ""),
                    "negative_prompt": result.get("negative_prompt", ""),
                    "method": "llm"
                }
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"LLM enhancement failed: {e}. Falling back to rule-based.")
            return super().enhance_prompt(simple_prompt)


def process_prompts_from_file(filepath: Path, enhancer: PromptEnhancer) -> List[dict]:
    """Process prompts from a text file (one prompt per line)."""
    results = []

    # Count total prompts first
    with open(filepath, 'r', encoding='utf-8') as f:
        total_prompts = sum(1 for line in f if line.strip() and not line.strip().startswith('#'))

    print(f"\nProcessing {total_prompts} prompts from {filepath}")
    print(f"{'='*60}\n")

    with open(filepath, 'r', encoding='utf-8') as f:
        current = 0
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and comments
                current += 1
                print(f"[{current}/{total_prompts}] Processing: {line[:50]}{'...' if len(line) > 50 else ''}")
                result = enhancer.enhance_prompt(line)
                results.append(result)
                print()  # Blank line between prompts

    print(f"{'='*60}")
    print(f"✓ Completed {len(results)}/{total_prompts} prompts")
    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Enhance image generation prompts for diffusion models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rule-based enhancement (no dependencies)
  python prompt_enhancer.py "a cat sitting on a windowsill"
  python prompt_enhancer.py --file prompts.txt --output enhanced.json
  python prompt_enhancer.py "a cat" --style photography --creativity 0.9

  # Local HuggingFace model (recommended for Mac)
  python prompt_enhancer.py "a cat" --use-hf
  python prompt_enhancer.py "a cat" --use-hf --hf-model Qwen/Qwen2.5-3B-Instruct
  python prompt_enhancer.py --list-hf-models  # Show recommended models

  # Anthropic API
  python prompt_enhancer.py "a cat" --use-llm --api-key sk-xxx

  # With LoRA trigger words
  python prompt_enhancer.py "unicorn" --style coloring-book --trigger-words "sketch, rough sketch, pen sketch" --use-hf
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("prompt", nargs='?', help="Single prompt to enhance")
    input_group.add_argument("--file", "-f", type=Path, help="File with prompts (one per line)")

    # Enhancement options
    parser.add_argument("--style", "-s",
                       choices=["auto", "photography", "artistic", "realistic", "cinematic", "coloring-book"],
                       default="auto",
                       help="Enhancement style (default: auto-detect)")
    parser.add_argument("--creativity", "-c", type=float, default=0.7,
                       help="Creativity level 0.0-1.0 (default: 0.7)")
    parser.add_argument("--trigger-words", "-t", type=str,
                       help="LoRA trigger words to include at start of prompt")

    # LLM options
    parser.add_argument("--use-llm", action="store_true",
                       help="Use Anthropic API for advanced enhancement")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--model", default="claude-3-5-sonnet-20241022",
                       help="Anthropic model to use (for --use-llm)")

    # HuggingFace local model options
    parser.add_argument("--use-hf", action="store_true",
                       help="Use local HuggingFace model for enhancement (optimized for Apple Silicon)")
    parser.add_argument("--hf-model", default="Qwen/Qwen2.5-3B-Instruct",
                       help="HuggingFace model ID (default: Qwen/Qwen2.5-3B-Instruct)")
    parser.add_argument("--list-hf-models", action="store_true",
                       help="Show recommended HuggingFace models and exit")

    # Output options
    parser.add_argument("--output", "-o", type=Path,
                       help="Save results to JSON file")
    parser.add_argument("--show-negative", action="store_true",
                       help="Show negative prompts in output")
    parser.add_argument("--json", action="store_true",
                       help="Output as JSON")

    args = parser.parse_args()

    # Show recommended models and exit
    if args.list_hf_models:
        print("Recommended HuggingFace Models for Prompt Enhancement:\n")
        print("1. Qwen/Qwen2.5-3B-Instruct (DEFAULT)")
        print("   - Best overall choice, matches Qwen-Image ecosystem")
        print("   - Size: 3B parameters (efficient on M4 Mac)")
        print("   - Excellent instruction-following and creativity\n")
        print("2. gokaygokay/Flux-Prompt-Enhance")
        print("   - Specialized for Flux/Stable Diffusion prompts")
        print("   - Size: ~8B parameters")
        print("   - Purpose-built for image generation\n")
        print("3. microsoft/Phi-3.5-mini-instruct")
        print("   - Most efficient option")
        print("   - Size: 3.8B parameters")
        print("   - Optimized for Apple Silicon\n")
        print("4. Qwen/Qwen2.5-7B-Instruct")
        print("   - Higher quality, larger model")
        print("   - Size: 7B parameters (works on 48GB RAM)")
        print("   - More detailed and creative enhancements\n")
        print("Usage: python prompt_enhancer.py 'a cat' --use-hf --hf-model MODEL_ID")
        sys.exit(0)

    # Validate mutually exclusive enhancement methods
    if args.use_llm and args.use_hf:
        print("Error: Cannot use both --use-llm and --use-hf. Choose one enhancement method.")
        sys.exit(1)

    # Initialize enhancer
    if args.use_hf:
        enhancer = HFPromptEnhancer(
            model_id=args.hf_model,
            style=args.style,
            creativity=args.creativity,
            trigger_words=args.trigger_words
        )
    elif args.use_llm:
        import os
        api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: --api-key required or set ANTHROPIC_API_KEY environment variable")
            sys.exit(1)

        enhancer = LLMPromptEnhancer(
            api_key=api_key,
            model=args.model,
            style=args.style,
            creativity=args.creativity,
            trigger_words=args.trigger_words
        )
    else:
        enhancer = PromptEnhancer(
            style=args.style,
            creativity=args.creativity,
            trigger_words=args.trigger_words
        )

    # Process prompts
    if args.file:
        results = process_prompts_from_file(args.file, enhancer)
    else:
        results = [enhancer.enhance_prompt(args.prompt)]

    # Output results
    if args.json or args.output:
        method = "rule-based"
        if args.use_llm:
            method = "llm"
        elif args.use_hf:
            method = "huggingface"

        output_data = {
            "settings": {
                "style": args.style,
                "creativity": args.creativity,
                "method": method,
                "model": args.hf_model if args.use_hf else (args.model if args.use_llm else None)
            },
            "prompts": results
        }

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(output_data, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        for i, result in enumerate(results, 1):
            if len(results) > 1:
                print(f"\n{'='*80}")
                print(f"Prompt {i}/{len(results)}")
                print(f"{'='*80}")

            print(f"\nOriginal: {result['original']}")
            print(f"\nEnhanced:\n{result['enhanced_prompt']}")

            if args.show_negative:
                print(f"\nNegative:\n{result['negative_prompt']}")

            if 'detected_style' in result:
                print(f"\nDetected style: {result['detected_style']}")

            if 'model' in result:
                print(f"Model: {result['model']}")
            elif 'method' in result:
                print(f"Method: {result['method']}")


if __name__ == "__main__":
    main()
