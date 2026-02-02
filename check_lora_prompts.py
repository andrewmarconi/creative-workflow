#!/usr/bin/env python
"""Quick script to check LoRA prompt_suffix values in the database."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'queerchaos.settings')
django.setup()

from queerchaos.diffusion.models import LoraModel

print("\n" + "="*60)
print("LoRA Models and their Prompt Suffixes")
print("="*60)

loras = LoraModel.objects.all()

if not loras:
    print("\nNo LoRA models found in database.")
else:
    for lora in loras:
        print(f"\nLoRA: {lora.label}")
        print(f"  Path: {lora.path}")
        print(f"  Prompt Suffix: '{lora.prompt_suffix}'")
        print(f"  Active: {lora.is_active}")

        if not lora.prompt_suffix:
            print("  ⚠️  WARNING: No prompt suffix set!")

print("\n" + "="*60 + "\n")
