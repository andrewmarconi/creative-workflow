#!/usr/bin/env python3
"""
Test SDXL Turbo with an actual SDXL LoRA (not Z-Image)

Using civitai_177996.safetensors which is confirmed SDXL format
"""
from diffusers import StableDiffusionXLPipeline
import torch
import numpy as np

print("=" * 60)
print("SDXL Turbo + Real SDXL LoRA Test")
print("=" * 60)

# Load SDXL Turbo
print("\n1. Loading SDXL Turbo...")
pipeline = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/sdxl-turbo",
    torch_dtype=torch.bfloat16,
    variant="fp16",
)

# Setup for MPS (matching the fix in sdxlturbo.py)
device = torch.device("mps")
print(f"\n2. Applying MPS optimizations (no CPU offload)...")

# Convert VAE to float32 FIRST
print(f"   Converting VAE to float32...")
pipeline.vae = pipeline.vae.to(dtype=torch.float32)
print(f"   VAE dtype: {pipeline.vae.dtype}")

# Move to device (no CPU offload)
print(f"   Moving pipeline to {device}...")
pipeline = pipeline.to(device)
pipeline.enable_attention_slicing()

# Test WITHOUT LoRA first
print("\n3. Testing WITHOUT LoRA...")
result = pipeline(
    prompt="a colorful illustration of a robot",
    num_inference_steps=4,
    guidance_scale=0.0,
)
img_array = np.array(result.images[0])
mean_val = img_array.mean()
print(f"   Mean pixel value: {mean_val:.2f}")
print(f"   Is black: {mean_val < 10}")
if mean_val >= 10:
    result.images[0].save("test_no_lora.jpg")
    print(f"   ✓ Saved test_no_lora.jpg")

# Load REAL SDXL LoRA
lora_path = "models/loras/civitai_177996.safetensors"
print(f"\n4. Loading SDXL LoRA: {lora_path}...")
pipeline.load_lora_weights(lora_path, adapter_name="default")
pipeline.set_adapters(["default"], adapter_weights=[0.8])
print(f"   ✓ LoRA loaded")

# Re-apply VAE fix after LoRA load (matching _post_lora_load_fixes)
print(f"\n5. Re-applying VAE float32 fix after LoRA load...")
pipeline.vae = pipeline.vae.to(device=device, dtype=torch.float32)
print(f"   VAE dtype: {pipeline.vae.dtype}")
print(f"   VAE device: {pipeline.vae.device}")

# Test WITH LoRA
print("\n6. Testing WITH LoRA...")
result = pipeline(
    prompt="a colorful illustration of a robot",
    num_inference_steps=4,
    guidance_scale=0.0,
)
img_array = np.array(result.images[0])
mean_val = img_array.mean()
print(f"   Mean pixel value: {mean_val:.2f}")
print(f"   Is black: {mean_val < 10}")
if mean_val >= 10:
    result.images[0].save("test_with_lora.jpg")
    print(f"   ✓ Saved test_with_lora.jpg")
    print(f"\n   SUCCESS! LoRA works without black images!")
else:
    result.images[0].save("test_with_lora_BLACK.jpg")
    print(f"\n   ✗ FAILED - still getting black images")

print("\n" + "=" * 60)
