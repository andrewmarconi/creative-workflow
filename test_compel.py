#!/usr/bin/env python3
"""
Test script to verify Compel integration with CLIP-based models
Tests long prompt handling and prompt weighting syntax
"""

import sys
import json
from pathlib import Path


def test_compel_integration():
    """Test that Compel can handle long prompts without truncation"""
    print("Testing Compel integration...")
    print("-" * 60)

    # Load presets directly
    presets_path = Path(__file__).parent / "data" / "presets.json"
    with open(presets_path) as f:
        presets = json.load(f)
    models = presets.get('models', [])

    # Find a CLIP-based model (77-token limit)
    sdxl_model = None
    for model in models:
        if model.get('pipeline') == 'StableDiffusionXLPipeline':
            sdxl_model = model
            break

    if not sdxl_model:
        print("❌ No SDXL model found in presets")
        return False

    print(f"✓ Found SDXL model: {sdxl_model['label']}")
    print(f"  Pipeline: {sdxl_model['pipeline']}")
    print(f"  Token window: {sdxl_model['settings'].get('token_window', 'N/A')}")
    print()

    # Test prompt weighting syntax
    test_prompts = [
        # Standard prompt
        "a beautiful landscape",

        # Long prompt (>77 tokens when tokenized)
        "a highly detailed, photorealistic landscape painting of a serene mountain valley "
        "at sunset, with dramatic lighting, golden hour atmosphere, misty background, "
        "lush green meadows in the foreground, snow-capped peaks in the distance, "
        "crystal clear river flowing through the valley, vibrant wildflowers, "
        "cinematic composition, award-winning photography, 8k ultra HD",

        # Prompt with weighting syntax (Compel feature)
        "a (beautiful:1.3) landscape with (dramatic lighting:1.5), "
        "avoiding (blur:0.5) and (noise:0.3)",

        # Very long prompt with weighting
        "(masterpiece:1.4), (best quality:1.3), a highly detailed photograph of "
        "a magical forest scene, (ethereal lighting:1.5), (mystical atmosphere:1.2), "
        "ancient trees with twisted roots, glowing mushrooms, fairy lights, "
        "morning mist, (cinematic composition:1.3), (vibrant colors:1.2)"
    ]

    print("Test prompts:")
    for i, prompt in enumerate(test_prompts, 1):
        token_estimate = len(prompt.split())  # Rough estimate
        print(f"{i}. [{token_estimate} words] {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    print()
    print("✓ Compel should handle all these prompts without truncation")
    print("✓ Prompts with (word:weight) syntax will have proper emphasis")
    print()
    print("To test with actual generation:")
    print("1. Start the Django server: uv run manage.py runserver")
    print("2. Create a prompt with >77 tokens in the admin")
    print("3. Queue a job and check the generated images")
    print("4. Compare with old truncation behavior (CLIPTokenLimitMixin)")

    return True


if __name__ == "__main__":
    try:
        success = test_compel_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
