"""
Django management command to import Segments from JSON file.

Reads Segment records from data/segments.json and imports them using
update_or_create (identified by unique key: category, vector, value).

Usage:
    uv run manage.py import_segments                        # Import from data/segments.json
    uv run manage.py import_segments --dir custom/          # Custom input directory
    uv run manage.py import_segments --dry-run              # Preview without importing
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.audiences.models import Segment


class Command(BaseCommand):
    help = "Import Segment records from segments.json"

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
        self.stdout.write("Loading segments...")
        self.stdout.write("=" * 60)

        file_path = input_dir / "segments.json"
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                segments_data = json.load(f)
        except json.JSONDecodeError:
            # Handle empty or invalid files as empty arrays
            self.stdout.write(self.style.WARNING(f"  Warning: {file_path.name} is empty or invalid, treating as empty array"))
            segments_data = []

        self.stdout.write(f"  ✓ Loaded {file_path}: {len(segments_data)} records")

        # Preview or import
        if is_dry_run:
            self._dry_run_preview(segments_data)
        else:
            self._do_import(segments_data)

    def _dry_run_preview(self, segments_data: list):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nSegments to import:")
        for item in segments_data[:5]:
            self.stdout.write(
                f"  - {item['category']}: {item['vector']} → {item['value']}"
            )
        if len(segments_data) > 5:
            self.stdout.write(f"  ... and {len(segments_data) - 5} more")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, segments_data: list):
        """Import all segments within a transaction."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing segments...")
        self.stdout.write("=" * 60)

        created_count = 0
        updated_count = 0

        for item in segments_data:
            obj, created = Segment.objects.update_or_create(
                category=item["category"],
                vector=item["vector"],
                value=item["value"],
                defaults={
                    "description": item.get("description", ""),
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
        self.stdout.write(f"  Segments created: {created_count}")
        self.stdout.write(f"  Segments updated: {updated_count}")
        self.stdout.write("=" * 60)
