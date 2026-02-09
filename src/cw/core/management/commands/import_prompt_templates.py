"""
Management command to import Jinja2 prompt templates from files into database.

Usage:
    python manage.py import_prompt_templates [--dry-run]
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from cw.core.models import PromptTemplate


class Command(BaseCommand):
    """Import .j2 template files into PromptTemplate model."""

    help = "Import Jinja2 prompt templates from src/cw/lib/prompts/ into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Template definitions: (slug, name, category, filename)
        templates = [
            (
                "prompt-enhancer-system",
                "Prompt Enhancer System",
                "enhancement",
                "prompt_enhancer_system.j2",
                "System prompt for HuggingFace and Anthropic prompt enhancers",
            ),
            (
                "prompt-enhancer-user",
                "Prompt Enhancer User",
                "enhancement",
                "prompt_enhancer_user.j2",
                "User prompt template for enhancement requests",
            ),
            (
                "adaptation",
                "Cultural Adaptation",
                "adaptation",
                "adaptation.j2",
                "Main cultural adaptation prompt for TV spot localization (104 lines)",
            ),
            (
                "concept-extraction",
                "Concept Extraction",
                "concept",
                "concept_extraction.j2",
                "Analyzes original TV spot script to extract core creative concept",
            ),
            (
                "cultural-research",
                "Cultural Research",
                "concept",
                "cultural_research.j2",
                "Produces cultural brief for target market adaptation",
            ),
            (
                "eval-concept",
                "Concept Evaluation",
                "evaluation",
                "eval_concept.j2",
                "Evaluates whether adaptation preserves original creative concept",
            ),
            (
                "eval-cultural",
                "Cultural Evaluation",
                "evaluation",
                "eval_cultural.j2",
                "Evaluates cultural appropriateness and authenticity of adaptation",
            ),
            (
                "eval-format",
                "Format Evaluation",
                "evaluation",
                "eval_format.j2",
                "Evaluates language compliance and formatting rules",
            ),
        ]

        # Find the prompts directory
        prompts_dir = Path(__file__).parent.parent.parent.parent / "lib" / "prompts"

        if not prompts_dir.exists():
            self.stderr.write(
                self.style.ERROR(f"Prompts directory not found: {prompts_dir}")
            )
            return

        self.stdout.write(f"Reading templates from: {prompts_dir}\n")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for slug, name, category, filename, description in templates:
                template_path = prompts_dir / filename

                if not template_path.exists():
                    self.stderr.write(
                        self.style.WARNING(f"File not found: {template_path}, skipping")
                    )
                    skipped_count += 1
                    continue

                # Read template content
                template_content = template_path.read_text()

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
