#!/usr/bin/env python3
"""
Quick test to debug SDXL Turbo + Compel integration
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from lib.models import ModelFactory
import json
from pathlib import Path

def test_sdxl_turbo_generation():
    """Test SDXL Turbo with Compel"""
    print("=" * 60)
    print("Testing SDXL Turbo + Compel Integration")
    print("=" * 60)

    # Load SDXL Turbo config
    presets_path = Path(__file__).parent / "data" / "presets.json"
    with open(presets_path) as f:
        presets = json.load(f)
    models = presets.get('models', [])

    sdxl_turbo = None
    for model in models:
        if model.get('slug') == 'sdxl_turbo':
            sdxl_turbo = model
            break

    if not sdxl_turbo:
        print("❌ SDXL Turbo not found in presets")
        return False

    print(f"\n✓ Found model: {sdxl_turbo['label']}")
    print(f"  Pipeline: {sdxl_turbo['pipeline']}")
    print(f"  Path: {sdxl_turbo['path']}")

    # Create model instance
    print("\nCreating model instance...")
    model_instance = ModelFactory.create_model(sdxl_turbo, sdxl_turbo['path'])

    print(f"✓ Model instance type: {type(model_instance).__name__}")
    print(f"✓ Uses CompelPromptMixin: {hasattr(model_instance, '_get_compel')}")

    # Load pipeline
    print("\nLoading pipeline...")
    status = model_instance.load_pipeline()
    print(f"Load status: {status}")

    # Check pipeline attributes
    pipeline = model_instance.pipeline
    print(f"\n✓ Pipeline loaded: {type(pipeline).__name__}")
    print(f"  Has text_encoder: {hasattr(pipeline, 'text_encoder')}")
    print(f"  Has text_encoder_2: {hasattr(pipeline, 'text_encoder_2')}")
    print(f"  Has tokenizer: {hasattr(pipeline, 'tokenizer')}")
    print(f"  Has tokenizer_2: {hasattr(pipeline, 'tokenizer_2')}")

    # Try a simple generation
    print("\n" + "=" * 60)
    print("Attempting generation (this will show Compel debug output)...")
    print("=" * 60)

    try:
        image, metadata = model_instance.generate(
            prompt="a photo of a cat",
            steps=4,  # SDXL Turbo default
            width=512,
            height=512,
        )

        print("\n✓ Generation completed!")
        print(f"  Image size: {image.size}")
        print(f"  Metadata: {metadata}")

        # Check if image is black
        import numpy as np
        img_array = np.array(image)
        is_black = img_array.max() < 10

        if is_black:
            print("  ❌ WARNING: Image appears to be black!")
        else:
            print("  ✓ Image has content (not black)")

        return not is_black

    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sdxl_turbo_generation()
    sys.exit(0 if success else 1)
