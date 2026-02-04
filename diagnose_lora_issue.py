#!/usr/bin/env python3
"""
Diagnostic script to check SDXL + LoRA on MPS

This will help identify where the black image issue is occurring.
"""
from diffusers import StableDiffusionXLPipeline
import torch
import numpy as np

print("=" * 60)
print("SDXL + LoRA MPS Diagnostic")
print("=" * 60)

# Device setup
device = torch.device("mps")
print(f"\n1. Device: {device}")
print(f"   MPS available: {torch.backends.mps.is_available()}")

# Load model
print("\n2. Loading SDXL Turbo...")
pipeline = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/sdxl-turbo",
    torch_dtype=torch.bfloat16,
    variant="fp16",
)

# Check component dtypes BEFORE optimizations
print("\n3. Component dtypes BEFORE optimizations:")
print(f"   UNet: {pipeline.unet.dtype}")
print(f"   VAE: {pipeline.vae.dtype}")
print(f"   Text Encoder: {pipeline.text_encoder.dtype}")

# Convert VAE to float32
print("\n4. Converting VAE to float32...")
pipeline.vae = pipeline.vae.to(dtype=torch.float32)
print(f"   VAE dtype after conversion: {pipeline.vae.dtype}")

# Move to device
print("\n5. Moving pipeline to MPS...")
pipeline = pipeline.to(device)
pipeline.enable_attention_slicing()

print(f"\n6. Component devices AFTER moving to MPS:")
print(f"   UNet device: {pipeline.unet.device}")
print(f"   VAE device: {pipeline.vae.device}")
print(f"   VAE dtype: {pipeline.vae.dtype}")

# Test WITHOUT LoRA
print("\n7. Testing generation WITHOUT LoRA...")
result = pipeline(
    prompt="a simple test image",
    num_inference_steps=4,
    guidance_scale=0.0,
)
img_array = np.array(result.images[0])
has_nans = np.isnan(img_array).any()
is_black = img_array.mean() < 10
print(f"   Has NaNs: {has_nans}")
print(f"   Is black (mean < 10): {is_black}, mean={img_array.mean():.2f}")
if not has_nans and not is_black:
    result.images[0].save("test_without_lora.jpg")
    print(f"   ✓ Saved test_without_lora.jpg")

# Load LoRA
lora_path = "models/loras/civitai_2550274.safetensors"  # Adjust to your LoRA path
print(f"\n8. Loading LoRA from {lora_path}...")
try:
    pipeline.load_lora_weights(lora_path, adapter_name="default")
    pipeline.set_adapters(["default"], adapter_weights=[0.8])
    print(f"   ✓ LoRA loaded")
except Exception as e:
    print(f"   ✗ Error loading LoRA: {e}")
    exit(1)

# Check component state AFTER LoRA
print(f"\n9. Component state AFTER LoRA loading:")
print(f"   UNet device: {pipeline.unet.device}")
print(f"   VAE device: {pipeline.vae.device}")
print(f"   VAE dtype: {pipeline.vae.dtype}")

# Test WITH LoRA
print("\n10. Testing generation WITH LoRA...")
result = pipeline(
    prompt="a retro vintage comic style robot",
    num_inference_steps=4,
    guidance_scale=0.0,
)
img_array = np.array(result.images[0])
has_nans = np.isnan(img_array).any()
is_black = img_array.mean() < 10
print(f"    Has NaNs: {has_nans}")
print(f"    Is black (mean < 10): {is_black}, mean={img_array.mean():.2f}")
if not has_nans and not is_black:
    result.images[0].save("test_with_lora.jpg")
    print(f"    ✓ Saved test_with_lora.jpg")
else:
    print(f"    ✗ BLACK IMAGE DETECTED")
    # Save anyway for inspection
    result.images[0].save("test_with_lora_BLACK.jpg")

print("\n" + "=" * 60)
print("Diagnostic complete!")
print("=" * 60)
