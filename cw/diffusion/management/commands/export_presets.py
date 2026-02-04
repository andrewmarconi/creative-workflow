"""
Django management command to export database models and LoRAs to presets.json.

Usage:
    python manage.py export_presets
    python manage.py export_presets --file path/to/output.json
    python manage.py export_presets --active-only
"""
import json
from django.core.management.base import BaseCommand, CommandError
from cw.diffusion.models import DiffusionModel, LoraModel
from pathlib import Path


class Command(BaseCommand):
    help = 'Export models and LoRAs from the database to presets.json format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/presets.json',
            help='Output file path (default: data/presets.json)'
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Only export active models and LoRAs'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        # Query models
        models_qs = DiffusionModel.objects.order_by('slug')
        if options['active_only']:
            models_qs = models_qs.filter(is_active=True)

        # Query LoRAs
        loras_qs = LoraModel.objects.order_by('base_architecture', 'label')
        if options['active_only']:
            loras_qs = loras_qs.filter(is_active=True)

        # Build models list
        models = []
        for model in models_qs:
            model_data = {
                'slug': model.slug,
                'label': model.label,
                'path': model.path,
                'pipeline': model.pipeline,
                'base_architecture': model.base_architecture,
                'settings': {
                    'steps': model.steps,
                    'guidance_scale': model.guidance_scale,
                    'default_width': model.default_width,
                    'default_height': model.default_height,
                    'max_pixels': model.max_pixels,
                    'dtype': model.dtype,
                    'supports_negative_prompt': model.supports_negative_prompt,
                }
            }

            # Add force_default_guidance if True
            if model.force_default_guidance:
                model_data['settings']['force_default_guidance'] = True

            # Add optional fields if present
            if model.scheduler:
                model_data['settings']['scheduler'] = model.scheduler
            if model.max_sequence_length:
                model_data['settings']['max_sequence_length'] = model.max_sequence_length
            if model.token_window:
                model_data['settings']['token_window'] = model.token_window
            if model.vram_usage:
                model_data['settings']['vram_usage'] = model.vram_usage

            models.append(model_data)

        # Build LoRAs list
        loras = []
        for lora in loras_qs:
            lora_data = {
                'label': lora.label,
                'base_architecture': lora.base_architecture,
                'settings': {
                    'strength': lora.default_strength,
                }
            }

            # Add theme if present
            if lora.theme:
                lora_data['theme'] = lora.theme

            # Add optional settings if present
            if lora.guidance_scale is not None:
                lora_data['settings']['guidance_scale'] = lora.guidance_scale
            if lora.clip_skip is not None:
                lora_data['settings']['clip_skip'] = lora.clip_skip

            # Add path if present
            if lora.path:
                lora_data['path'] = lora.path

            # Add AIR if present
            if lora.air:
                lora_data['air'] = lora.air

            # Add prompt suffixes if present
            if lora.prompt_suffix:
                lora_data['prompt'] = lora.prompt_suffix
            if lora.negative_prompt_suffix:
                lora_data['negative_prompt'] = lora.negative_prompt_suffix

            # Add notes if present
            if lora.notes:
                lora_data['notes'] = lora.notes

            loras.append(lora_data)

        if not models and not loras:
            raise CommandError("No models or LoRAs to export")

        # Build final presets structure
        presets = {
            'models': models,
            'loras': loras
        }

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Exported {len(models)} models and {len(loras)} LoRAs")
        self.stdout.write(f"  Output file: {file_path}")
        self.stdout.write("="*60)
