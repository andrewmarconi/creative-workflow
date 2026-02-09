"""
Django management command to import Brands from JSON file.

Reads Brand records from data/brands.json and imports them using
update_or_create (identified by unique key: code).

Usage:
    uv run manage.py import_brands                        # Import from data/brands.json
    uv run manage.py import_brands --dir custom/          # Custom input directory
    uv run manage.py import_brands --dry-run              # Preview without importing
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.tvspots.models import Brand


class Command(BaseCommand):
    help = "Import Brand records from brands.json"

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

        # Load data file
        self.stdout.write("=" * 60)
        self.stdout.write("Loading brands...")
        self.stdout.write("=" * 60)

        file_path = input_dir / "brands.json"
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                brands_data = json.load(f)
        except json.JSONDecodeError:
            self.stdout.write(self.style.WARNING(f"  Warning: {file_path.name} is empty or invalid, treating as empty array"))
            brands_data = []

        self.stdout.write(f"  Loaded {file_path}: {len(brands_data)} records")

        # Preview or import
        if is_dry_run:
            self._dry_run_preview(brands_data)
        else:
            self._do_import(brands_data)

    def _dry_run_preview(self, brands_data: list):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nBrands to import:")
        for item in brands_data[:5]:
            self.stdout.write(
                f"  - {item['code']}: {item['name']}"
            )
        if len(brands_data) > 5:
            self.stdout.write(f"  ... and {len(brands_data) - 5} more")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, brands_data: list):
        """Import all brands within a transaction."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing brands...")
        self.stdout.write("=" * 60)

        created_count = 0
        updated_count = 0

        for item in brands_data:
            obj, created = Brand.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "guidelines": item.get("guidelines", ""),
                    "insights": item.get("insights", []),
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Brands created: {created_count}")
        self.stdout.write(f"  Brands updated: {updated_count}")
        self.stdout.write("=" * 60)
