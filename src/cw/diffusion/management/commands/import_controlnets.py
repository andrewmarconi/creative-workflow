"""
Django management command to import ControlNet models from JSON file.

Reads ControlNetModel records from data/controlnet_models.json and imports them
using update_or_create (identified by unique key: slug).

Usage:
    uv run manage.py import_controlnets                        # Import from data/controlnet_models.json
    uv run manage.py import_controlnets --dir custom/          # Custom input directory
    uv run manage.py import_controlnets --dry-run              # Preview without importing
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.diffusion.models import ControlNetModel


class Command(BaseCommand):
    help = "Import ControlNet model records from controlnet_models.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Input directory containing JSON file (default: data/)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying database",
        )

    def handle(self, *args, **options):
        input_dir = Path(options["dir"])
        is_dry_run = options["dry_run"]

        self.stdout.write("=" * 60)
        self.stdout.write("Loading ControlNet models...")
        self.stdout.write("=" * 60)

        file_path = input_dir / "controlnet_models.json"
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.WARNING(
                    f"  Warning: {file_path.name} is empty or invalid, treating as empty array"
                )
            )
            data = []

        self.stdout.write(f"  Loaded {file_path}: {len(data)} records")

        if is_dry_run:
            self._dry_run_preview(data)
        else:
            self._do_import(data)

    def _dry_run_preview(self, data: list):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nControlNet models to import:")
        for item in data[:10]:
            self.stdout.write(
                f"  - {item['slug']}: {item['label']} ({item['control_type']}/{item['base_architecture']})"
            )
        if len(data) > 10:
            self.stdout.write(f"  ... and {len(data) - 10} more")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, data: list):
        """Import all ControlNet models within a transaction."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing ControlNet models...")
        self.stdout.write("=" * 60)

        created_count = 0
        updated_count = 0

        for item in data:
            obj, created = ControlNetModel.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "label": item["label"],
                    "path": item["path"],
                    "control_type": item["control_type"],
                    "base_architecture": item["base_architecture"],
                    "default_conditioning_scale": item.get("default_conditioning_scale", 0.5),
                    "default_guidance_end": item.get("default_guidance_end", 1.0),
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  ControlNet models created: {created_count}")
        self.stdout.write(f"  ControlNet models updated: {updated_count}")
        self.stdout.write("=" * 60)
