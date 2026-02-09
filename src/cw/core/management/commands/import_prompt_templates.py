"""
Management command to import prompt templates from JSON into database.

Reads from data/prompt_templates.json (exported via export_prompt_templates).

Usage:
    python manage.py import_prompt_templates [--dry-run] [--dir custom/]
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from cw.core.models import PromptTemplate


class Command(BaseCommand):
    """Import prompt templates from JSON into PromptTemplate model."""

    help = "Import prompt templates from data/prompt_templates.json into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--dir",
            type=str,
            default="",
            help="Custom directory to read from (default: data/)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        custom_dir = options["dir"]

        # Locate the JSON file
        if custom_dir:
            json_path = Path(custom_dir) / "prompt_templates.json"
        else:
            json_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "data" / "prompt_templates.json"

        if not json_path.exists():
            self.stderr.write(
                self.style.ERROR(f"File not found: {json_path}")
            )
            return

        self.stdout.write(f"Reading templates from: {json_path}\n")

        with open(json_path) as f:
            templates = json.load(f)

        if not isinstance(templates, list):
            self.stderr.write(self.style.ERROR("Expected a JSON array"))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for entry in templates:
                slug = entry["slug"]
                name = entry["name"]
                category = entry["category"]
                template_content = entry["template"]
                description = entry.get("description", "")

                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would import: {slug} ({len(template_content)} chars)"
                    )
                    continue

                # Check if template already exists
                try:
                    existing = PromptTemplate.objects.get(slug=slug, is_active=True)

                    # Compare content to see if update is needed
                    if existing.template == template_content:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ {slug}: Already up-to-date (v{existing.version})"
                            )
                        )
                        skipped_count += 1
                    else:
                        # Content changed - save will auto-create new version
                        existing.template = template_content
                        existing.description = description
                        existing.save()
                        # Refresh to get new version number
                        existing.refresh_from_db()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"↑ {slug}: Updated to v{existing.version} "
                                f"({len(template_content)} chars)"
                            )
                        )
                        updated_count += 1

                except PromptTemplate.DoesNotExist:
                    # Create new template
                    PromptTemplate.objects.create(
                        slug=slug,
                        name=name,
                        category=category,
                        template=template_content,
                        description=description,
                        version=1,
                        is_active=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"+ {slug}: Created v1 ({len(template_content)} chars)"
                        )
                    )
                    created_count += 1

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "\n[DRY RUN] No changes made. Run without --dry-run to import."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Import complete: {created_count} created, "
                        f"{updated_count} updated, {skipped_count} skipped"
                    )
                )
