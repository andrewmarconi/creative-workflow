#!/usr/bin/env python3
"""
Inspect LoRA file structure to understand format
"""
from safetensors import safe_open
from pathlib import Path

lora_path = Path("models/loras/civitai_2550274.safetensors")

print(f"Inspecting: {lora_path}")
print(f"File size: {lora_path.stat().st_size / 1024 / 1024:.1f} MB\n")

with safe_open(lora_path, framework="pt", device="cpu") as f:
    keys = list(f.keys())
    print(f"Total keys: {len(keys)}\n")

    # Sample first 20 keys
    print("First 20 keys:")
    for i, key in enumerate(keys[:20]):
        tensor = f.get_tensor(key)
        print(f"  {key}: {tensor.shape}")

    # Look for key patterns
    print("\n\nKey patterns:")
    patterns = {}
    for key in keys:
        prefix = key.split('.')[0] if '.' in key else key
        patterns[prefix] = patterns.get(prefix, 0) + 1

    for pattern, count in sorted(patterns.items()):
        print(f"  {pattern}.*: {count} keys")

    # Check for specific model components
    print("\n\nComponent detection:")
    has_unet = any('unet' in k.lower() or 'down_blocks' in k or 'up_blocks' in k for k in keys)
    has_text_encoder = any('text_encoder' in k.lower() or 'text_model' in k for k in keys)
    has_lora_up = any('lora_up' in k for k in keys)
    has_lora_down = any('lora_down' in k for k in keys)

    print(f"  Has UNet keys: {has_unet}")
    print(f"  Has Text Encoder keys: {has_text_encoder}")
    print(f"  Has lora_up keys: {has_lora_up}")
    print(f"  Has lora_down keys: {has_lora_down}")

    # Determine format
    print("\n\nFormat detection:")
    if has_lora_up and has_lora_down:
        print("  ✓ Format: Kohya/A1111 style (lora_up/lora_down)")
    else:
        print("  Format: Unknown or diffusers native")
