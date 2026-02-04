#!/usr/bin/env python3
"""
Test SDXL Turbo with fp16-fix VAE on MPS
"""
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
import torch
import numpy as np

print("=" * 60)
print("SDXL Turbo + fp16-fix VAE Test")
print("=" * 60)

# Load the numerically stable VAE
print("\n1. Loading sdxl-vae-fp16-fix...")
vae = AutoencoderKL.from_pretrained(
    "madebyollin/sdxl-vae-fp16-fix",
    torch_dtype=torch.bfloat16  # Match pipeline dtype
)

# Load SDXL Turbo with the fixed VAE
print("\n2. Loading SDXL Turbo with fixed VAE...")
pipeline = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/sdxl-turbo",
    vae=vae,  # Use the fixed VAE
    torch_dtype=torch.bfloat16,
    variant="fp16",
)

# Setup for MPS
device = torch.device("mps")
print(f"\n3. Moving to {device} (no CPU offload, no VAE conversion)...")
pipeline = pipeline.to(device)
pipeline.enable_attention_slicing()

print(f"   VAE dtype: {pipeline.vae.dtype}")
print(f"   UNet dtype: {pipeline.unet.dtype}")

# Test WITHOUT LoRA
print("\n4. Testing WITHOUT LoRA...")
result = pipeline(
    prompt="a colorful illustration of a robot",
    num_inference_steps=4,
    guidance_scale=0.0,
)
img_array = np.array(result.images[0])
mean_val = img_array.mean()
print(f"   Mean pixel value: {mean_val:.2f}")
print(f"   Has NaNs: {np.isnan(img_array).any()}")
print(f"   Is black: {mean_val < 10}")
if mean_val >= 10:
    result.images[0].save("test_fp16vae_no_lora.jpg")
    print(f"   ✓ Saved test_fp16vae_no_lora.jpg - SUCCESS!")
else:
    print(f"   ✗ Still black")
    result.images[0].save("test_fp16vae_no_lora_BLACK.jpg")

# Only test with LoRA if no-LoRA worked
if mean_val >= 10:
    # Load REAL SDXL LoRA
    lora_path = "models/loras/civitai_177996.safetensors"
    print(f"\n5. Loading SDXL LoRA: {lora_path}...")
    try:
        pipeline.load_lora_weights(lora_path, adapter_name="default")
        pipeline.set_adapters(["default"], adapter_weights=[0.8])
        print(f"   ✓ LoRA loaded")

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
        print(f"   Has NaNs: {np.isnan(img_array).any()}")
        print(f"   Is black: {mean_val < 10}")
        if mean_val >= 10:
            result.images[0].save("test_fp16vae_with_lora.jpg")
            print(f"   ✓ Saved test_fp16vae_with_lora.jpg - SUCCESS!")
        else:
            result.images[0].save("test_fp16vae_with_lora_BLACK.jpg")
            print(f"   ✗ Still black with LoRA")
    except Exception as e:
        print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
