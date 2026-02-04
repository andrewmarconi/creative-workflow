#!/usr/bin/env python3
"""
Test SDXL with the fp16-fix VAE to avoid NaN/black images on MPS

This uses madebyollin/sdxl-vae-fp16-fix which is numerically stable.
"""
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
import torch
from pathlib import Path
import os

# Find the LoRA file
base_path = Path(os.getenv('MODEL_BASE_PATH', 'models'))
lora_path = base_path / 'loras' / 'civitai_2550274.safetensors'

print(f"Looking for LoRA at: {lora_path}")
if not lora_path.exists():
    print(f"ERROR: LoRA file not found!")
    # List available LoRAs
    lora_dir = base_path / 'loras'
    if lora_dir.exists():
        print(f"\nAvailable LoRAs in {lora_dir}:")
        for f in lora_dir.glob('*.safetensors'):
            print(f"  - {f.name}")
    exit(1)

print("Loading fixed VAE...")
# Load the fixed VAE
vae = AutoencoderKL.from_pretrained(
    "madebyollin/sdxl-vae-fp16-fix",
    torch_dtype=torch.float16
)

print("Loading SDXL Turbo...")
# Load SDXL Turbo with the fixed VAE
pipeline = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/sdxl-turbo",
    vae=vae,
    torch_dtype=torch.bfloat16,
    variant="fp16",
)

# Setup for MPS
device = torch.device("mps")
print(f"Moving to {device}...")
pipeline = pipeline.to(device)
pipeline.enable_attention_slicing()

# Try to load LoRA
print(f"\nLoading LoRA from {lora_path}...")
try:
    # Try loading without specifying adapter_name first
    pipeline.load_lora_weights(str(lora_path))
    print("✓ LoRA loaded successfully")

    # Check if adapters were actually loaded
    if hasattr(pipeline, '_lora_scale'):
        print(f"  LoRA scale: {pipeline._lora_scale}")

    # Try to set adapter if it exists
    try:
        pipeline.set_adapters(["default"], adapter_weights=[0.8])
        print("✓ Adapter set to 0.8 strength")
    except ValueError as e:
        print(f"  Note: Could not set adapter explicitly: {e}")
        print("  LoRA may still be applied with default strength")

except Exception as e:
    print(f"✗ Error loading LoRA: {e}")
    print("\nTrying alternative loading method...")
    try:
        # Try loading as single file
        from diffusers.loaders import FromSingleFileMixin
        pipeline.unet.load_attn_procs(str(lora_path))
        print("✓ LoRA loaded via alternative method")
    except Exception as e2:
        print(f"✗ Alternative method also failed: {e2}")
        print("\nContinuing without LoRA...")

# Generate
print("\nGenerating image...")
prompt = "a retro vintage comic style illustration of a robot"
image = pipeline(
    prompt=prompt,
    num_inference_steps=9,
    guidance_scale=0.0,
).images[0]

image.save("test_vae_fix.jpg")
print("✓ Generated test_vae_fix.jpg")

# Check if image is black
import numpy as np
img_array = np.array(image)
mean_val = img_array.mean()
print(f"\nImage statistics:")
print(f"  Mean pixel value: {mean_val:.2f}")
print(f"  Is black (mean < 10): {mean_val < 10}")
print(f"  Has NaNs: {np.isnan(img_array).any()}")
