"""
Django management command to import presets.json into database.

Usage:
    python manage.py import_presets
    python manage.py import_presets --file path/to/presets.json
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.diffusion.models import DiffusionModel, LoraModel


class Command(BaseCommand):
    help = "Import models and LoRAs from presets.json into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/presets.json",
            help="Path to presets.json file (default: data/presets.json)",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing models and LoRAs before importing"
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading presets from: {file_path}")

        # Load presets
        with open(file_path, "r") as f:
            presets = json.load(f)

        # Clear existing data if requested
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing models and LoRAs..."))
            DiffusionModel.objects.all().delete()
            LoraModel.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        # Import within transaction
        with transaction.atomic():
            # Import models
            models_created = 0
            models_updated = 0

            self.stdout.write("\nImporting Diffusion Models:")
            for model_data in presets.get("models", []):
                settings = model_data.get("settings", {})

                model, created = DiffusionModel.objects.update_or_create(
                    slug=model_data["slug"],
                    defaults={
                        "label": model_data["label"],
                        "path": model_data["path"],
                        "pipeline": model_data["pipeline"],
                        "base_architecture": model_data.get("base_architecture", "sdxl"),
                        "steps": settings.get("steps", 28),
                        "guidance_scale": settings.get("guidance_scale", 3.5),
                        "force_default_guidance": settings.get("force_default_guidance", False),
                        "default_width": settings.get("default_width", 1024),
                        "default_height": settings.get("default_height", 1024),
                        "max_pixels": settings.get("max_pixels", 1048576),
                        "scheduler": settings.get("scheduler"),
                        "dtype": settings.get("dtype", "bfloat16"),
                        "supports_negative_prompt": settings.get("supports_negative_prompt", False),
                        "max_sequence_length": settings.get("max_sequence_length"),
                        "token_window": settings.get("token_window"),
                        "vram_usage": settings.get("vram_usage"),
                        "is_active": True,
                    },
                )

                if created:
                    models_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Created: {model.label} ({model.slug})")
                    )
                else:
                    models_updated += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ↻ Updated: {model.label} ({model.slug})")
                    )

            # Import LoRAs
            loras_created = 0
            loras_updated = 0

            self.stdout.write("\nImporting LoRA Models:")
            for lora_data in presets.get("loras", []):
                settings = lora_data.get("settings", {})

                # Use AIR as lookup key if path is empty
                if lora_data.get("path"):
                    lookup = {"path": lora_data["path"]}
                elif lora_data.get("air"):
                    lookup = {"air": lora_data["air"]}
                else:
                    lookup = {"label": lora_data["label"]}

                base_arch = lora_data.get("base_architecture", "sdxl")

                defaults_dict = {
                    "label": lora_data["label"],
                    "path": lora_data.get("path", ""),
                    "air": lora_data.get("air", ""),
                    "base_architecture": base_arch,
                    "theme": lora_data.get("theme", ""),
                    "prompt_suffix": lora_data.get("prompt", ""),
                    "negative_prompt_suffix": lora_data.get("negative_prompt", ""),
                    "default_strength": settings.get("strength", 0.8),
                    "notes": lora_data.get("notes", ""),
                    "is_active": True,
                }

                # Add optional fields if present
                if "guidance_scale" in settings:
                    defaults_dict["guidance_scale"] = settings["guidance_scale"]
                if "clip_skip" in settings:
                    defaults_dict["clip_skip"] = settings["clip_skip"]

                lora, created = LoraModel.objects.update_or_create(**lookup, defaults=defaults_dict)

                if created:
                    loras_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Created: {lora.label} (arch: {base_arch})")
                    )
                else:
                    loras_updated += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ↻ Updated: {lora.label} (arch: {base_arch})")
                    )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Models: {models_created} created, {models_updated} updated")
        self.stdout.write(f"  LoRAs:  {loras_created} created, {loras_updated} updated")
        self.stdout.write("=" * 60)
