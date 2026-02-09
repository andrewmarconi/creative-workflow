"""
Management command to export PromptTemplate records to JSON file.

Usage:
    python manage.py export_prompt_templates [--dir DIR] [--dry-run]
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.core.models import PromptTemplate


class Command(BaseCommand):
    """Export active PromptTemplate records to JSON file."""

    help = "Export prompt templates from database to data/prompt_templates.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Directory to export to (default: data/)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be exported without writing file",
        )

    def handle(self, **options):
        dry_run = options["dry_run"]
        export_dir = Path(options["dir"])

        # Get all active templates ordered by category and slug
        templates = PromptTemplate.objects.filter(is_active=True).order_by(
            "category", "slug"
        )

        if not templates.exists():
            self.stdout.write(
                self.style.WARNING("No active templates found in database")
            )
            return

        # Build export data
        export_data = []
        for template in templates:
            export_data.append(
                {
                    "slug": template.slug,
                    "name": template.name,
                    "category": template.category,
                    "description": template.description,
                    "template": template.template,
                    "expected_variables": template.expected_variables,
                    "version": template.version,
                }
            )

        # Show summary
        self.stdout.write(f"\nExporting {len(export_data)} active templates:\n")
        for item in export_data:
            self.stdout.write(
                f"  • {item['slug']} (v{item['version']}) - {item['category']}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would export to {export_dir}/prompt_templates.json"
                )
            )
            return

        # Create export directory if needed
        export_dir.mkdir(parents=True, exist_ok=True)

        # Write to file
        output_file = export_dir / "prompt_templates.json"
        with output_file.open("w") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Exported to {output_file} ({len(export_data)} templates)")
        )
