"""
Django management command to export Segments to JSON file.

Exports all Segment records to data/segments.json.

Usage:
    uv run manage.py export_segments                    # Export to data/segments.json
    uv run manage.py export_segments --dir custom/      # Custom output directory
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.audiences.models import Segment


class Command(BaseCommand):
    help = "Export Segment records to segments.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Output directory for JSON file (default: data/)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("=" * 60)
        self.stdout.write("Exporting segments...")
        self.stdout.write("=" * 60)

        segments = []
        for segment in Segment.objects.all().order_by("category", "vector", "value"):
            segments.append(
                {
                    "category": segment.category,
                    "vector": segment.vector,
                    "value": segment.value,
                    "description": segment.description,
                    "insights": segment.insights,
                    "is_active": segment.is_active,
                }
            )

        file_path = output_dir / "segments.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Output file: {file_path.absolute()}")
        self.stdout.write(f"  Segments: {len(segments)}")
        self.stdout.write("=" * 60)
