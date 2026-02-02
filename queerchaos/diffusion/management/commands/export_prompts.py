"""
Django management command to export prompts to a JSON file.

Usage:
    uv run manage.py export_prompts --file data/prompts.json
    uv run manage.py export_prompts --file data/prompts.json --enhanced-only
"""
import json
from django.core.management.base import BaseCommand, CommandError
from queerchaos.diffusion.models import Prompt
from pathlib import Path


class Command(BaseCommand):
    help = 'Export prompts from the database to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/prompts.json',
            help='Output file path (default: data/prompts.json)'
        )
        parser.add_argument(
            '--enhanced-only',
            action='store_true',
            help='Only export prompts that have been enhanced'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        queryset = Prompt.objects.order_by('id')
        if options['enhanced_only']:
            queryset = queryset.exclude(enhanced_prompt='')

        prompts = []
        for p in queryset:
            prompts.append({
                'source_prompt': p.source_prompt,
                'enhanced_prompt': p.enhanced_prompt,
                'negative_prompt': p.negative_prompt,
                'enhancement_style': p.enhancement_style,
                'creativity': p.creativity,
            })

        if not prompts:
            raise CommandError("No prompts to export")

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"Exported {len(prompts)} prompts to {file_path}"))
