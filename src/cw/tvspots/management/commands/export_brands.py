"""
Django management command to export Brands to JSON file.

Exports all Brand records to data/brands.json.

Usage:
    uv run manage.py export_brands                    # Export to data/brands.json
    uv run manage.py export_brands --dir custom/      # Custom output directory
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.tvspots.models import Brand


class Command(BaseCommand):
    help = "Export Brand records to brands.json"

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
        self.stdout.write("Exporting brands...")
        self.stdout.write("=" * 60)

        brands = []
        for brand in Brand.objects.all().order_by("name"):
            brands.append(
                {
                    "code": brand.code,
                    "name": brand.name,
                    "description": brand.description,
                    "guidelines": brand.guidelines,
                    "insights": brand.insights,
                    "is_active": brand.is_active,
                }
            )

        file_path = output_dir / "brands.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(brands, f, indent=2, ensure_ascii=False)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Output file: {file_path.absolute()}")
        self.stdout.write(f"  Brands: {len(brands)}")
        self.stdout.write("=" * 60)
