"""
Django management command to import presets.json into database.

Usage:
    python manage.py import_presets
    python manage.py import_presets --file path/to/presets.json
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from queerchaos.diffusion.models import DiffusionModel, LoraModel
from pathlib import Path
import json


class Command(BaseCommand):
    help = 'Import models and LoRAs from presets.json into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/presets.json',
            help='Path to presets.json file (default: data/presets.json)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing models and LoRAs before importing'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading presets from: {file_path}")

        # Load presets
        with open(file_path, 'r') as f:
            presets = json.load(f)

        # Clear existing data if requested
        if options['clear']:
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
            for model_data in presets.get('models', []):
                settings = model_data.get('settings', {})

                model, created = DiffusionModel.objects.update_or_create(
                    slug=model_data['slug'],
                    defaults={
                        'label': model_data['label'],
                        'path': model_data['path'],
                        'pipeline': model_data['pipeline'],
                        'steps': settings.get('steps', 28),
                        'guidance_scale': settings.get('guidance_scale', 3.5),
                        'default_width': settings.get('default_width', 1024),
                        'default_height': settings.get('default_height', 1024),
                        'max_pixels': settings.get('max_pixels', 1048576),
                        'scheduler': settings.get('scheduler'),
                        'dtype': settings.get('dtype', 'bfloat16'),
                        'supports_negative_prompt': settings.get('supports_negative_prompt', False),
                        'max_sequence_length': settings.get('max_sequence_length'),
                        'is_active': True,
                    }
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
            for lora_data in presets.get('loras', []):
                settings = lora_data.get('settings', {})

                lora, created = LoraModel.objects.update_or_create(
                    path=lora_data['path'],
                    defaults={
                        'label': lora_data['label'],
                        'air': lora_data.get('air', ''),
                        'prompt_suffix': lora_data.get('prompt', ''),
                        'default_strength': settings.get('strength', 0.8),
                        'is_active': True,
                    }
                )

                # Set compatibility
                compatibility_slugs = lora_data.get('compatibility', [])
                compatible_models = DiffusionModel.objects.filter(
                    slug__in=compatibility_slugs
                )
                lora.compatible_models.set(compatible_models)

                if created:
                    loras_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Created: {lora.label} "
                            f"(compatible with: {', '.join(compatibility_slugs)})"
                        )
                    )
                else:
                    loras_updated += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↻ Updated: {lora.label} "
                            f"(compatible with: {', '.join(compatibility_slugs)})"
                        )
                    )

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Models: {models_created} created, {models_updated} updated")
        self.stdout.write(f"  LoRAs:  {loras_created} created, {loras_updated} updated")
        self.stdout.write("="*60)
