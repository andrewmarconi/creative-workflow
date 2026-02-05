"""
Django management command to import prompts from a JSON or text file.

Usage:
    uv run manage.py import_prompts --file data/prompts.json
    uv run manage.py import_prompts --file data/prompts.txt --style coloring-book
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.diffusion.models import Prompt


class Command(BaseCommand):
    help = "Import prompts from a JSON or text file into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, required=True, help="Path to prompts file (.json or .txt)"
        )
        parser.add_argument(
            "--style",
            type=str,
            default="auto",
            choices=["auto", "photography", "artistic", "realistic", "cinematic", "coloring-book"],
            help="Enhancement style for imported prompts (default: auto, only used for .txt files)",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing prompts before importing"
        )
        parser.add_argument(
            "--skip-duplicates",
            action="store_true",
            help="Skip prompts that already exist (based on source_prompt)",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading prompts from: {file_path}")

        # Load prompts based on file type
        if file_path.suffix == ".json":
            prompts = self._load_json(file_path)
        else:
            prompts = self._load_text(file_path, options["style"])

        if not prompts:
            raise CommandError("No prompts found in file")

        self.stdout.write(f"Found {len(prompts)} prompts to import")

        # Clear existing prompts if requested
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing prompts..."))
            Prompt.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared."))

        # Import prompts
        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for idx, prompt_data in enumerate(prompts, 1):
                source = prompt_data["source_prompt"]

                if options["skip_duplicates"]:
                    if Prompt.objects.filter(source_prompt=source).exists():
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [{idx}/{len(prompts)}] Skipped (duplicate): {source[:60]}..."
                            )
                        )
                        continue

                Prompt.objects.create(
                    source_prompt=source,
                    enhanced_prompt=prompt_data.get("enhanced_prompt", ""),
                    negative_prompt=prompt_data.get("negative_prompt", ""),
                    enhancement_style=prompt_data.get("enhancement_style", "auto"),
                    enhancement_method=(
                        prompt_data.get("enhancement_method", "none")
                        if not prompt_data.get("enhanced_prompt")
                        else prompt_data.get("enhancement_method", "huggingface")
                    ),
                    creativity=prompt_data.get("creativity", 0.7),
                )
                created_count += 1

                if created_count % 10 == 0:
                    self.stdout.write(f"  Imported {created_count}/{len(prompts)}...")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Created: {created_count}")
        if skipped_count > 0:
            self.stdout.write(f"  Skipped (duplicates): {skipped_count}")
        self.stdout.write("=" * 60)

    def _load_json(self, file_path: Path) -> list:
        """Load prompts from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise CommandError("JSON file must contain a list of prompt objects")

        return data

    def _load_text(self, file_path: Path, style: str) -> list:
        """Load prompts from a plain text file (one per line)."""
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return [
            {"source_prompt": line.strip(), "enhancement_style": style}
            for line in lines
            if line.strip()
        ]
