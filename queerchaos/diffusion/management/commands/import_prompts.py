"""
Django management command to import prompts from a text file.

Usage:
    uv run manage.py import_prompts --file path/to/prompts.txt --style coloring-book
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from queerchaos.diffusion.models import Prompt
from pathlib import Path


class Command(BaseCommand):
    help = 'Import prompts from a text file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to text file with prompts (one per line)'
        )
        parser.add_argument(
            '--style',
            type=str,
            default='auto',
            choices=['auto', 'photography', 'artistic', 'realistic', 'cinematic', 'coloring-book'],
            help='Enhancement style for imported prompts (default: auto)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing prompts before importing'
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='Skip prompts that already exist (based on source_prompt)'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading prompts from: {file_path}")

        # Read prompts from file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filter out empty lines and strip whitespace
        prompts = [line.strip() for line in lines if line.strip()]

        if not prompts:
            raise CommandError("No prompts found in file")

        self.stdout.write(f"Found {len(prompts)} prompts to import")

        # Clear existing prompts if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING("Clearing existing prompts..."))
            Prompt.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        # Import prompts
        created_count = 0
        skipped_count = 0
        style = options['style']

        with transaction.atomic():
            for idx, prompt_text in enumerate(prompts, 1):
                # Skip if duplicate checking is enabled
                if options['skip_duplicates']:
                    if Prompt.objects.filter(source_prompt=prompt_text).exists():
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"  [{idx}/{len(prompts)}] Skipped (duplicate): {prompt_text[:60]}...")
                        )
                        continue

                # Create prompt
                Prompt.objects.create(
                    source_prompt=prompt_text,
                    enhancement_style=style,
                    enhancement_method='none',  # Not enhanced yet
                )
                created_count += 1

                # Show progress every 10 prompts
                if created_count % 10 == 0:
                    self.stdout.write(f"  Imported {created_count}/{len(prompts)}...")

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Created: {created_count}")
        if skipped_count > 0:
            self.stdout.write(f"  Skipped (duplicates): {skipped_count}")
        self.stdout.write(f"  Enhancement Style: {style}")
        self.stdout.write("="*60)
