#!/usr/bin/env python
"""Update LoRA paths to use absolute paths from ComfyUI directory."""
import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queerchaos.settings')
django.setup()

from queerchaos.diffusion.models import LoraModel

# Base path for LoRA files
COMFYUI_LORA_BASE = Path.home() / "Documents" / "ComfyUI" / "models" / "loras"

print("\n" + "="*60)
print("Updating LoRA Paths to Absolute Paths")
print("="*60)
print(f"\nBase directory: {COMFYUI_LORA_BASE}\n")

loras = LoraModel.objects.all()

if not loras:
    print("No LoRA models found in database.")
else:
    updated_count = 0
    not_found_count = 0

    for lora in loras:
        old_path = lora.path

        # Extract just the filename from the relative path
        filename = Path(old_path).name

        # Construct new absolute path
        new_path = COMFYUI_LORA_BASE / filename

        # Check if file exists
        if new_path.exists():
            print(f"✅ {lora.label}")
            print(f"   Old: {old_path}")
            print(f"   New: {new_path}")

            # Update the database
            lora.path = str(new_path)
            lora.save()
            updated_count += 1
        else:
            print(f"❌ {lora.label}")
            print(f"   File not found: {new_path}")
            not_found_count += 1

        print()

    print("="*60)
    print(f"Summary:")
    print(f"  ✅ Updated: {updated_count}")
    print(f"  ❌ Not found: {not_found_count}")
    print("="*60 + "\n")
