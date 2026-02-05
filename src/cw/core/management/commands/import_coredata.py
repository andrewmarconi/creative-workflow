"""
Django management command to import core data (languages and LLM models).

Supports both JSON and CSV formats.

Usage:
    uv run manage.py import_coredata                              # Default: data/core_data.json
    uv run manage.py import_coredata --file data/custom.json      # Custom JSON file
    uv run manage.py import_coredata --csv languages.csv          # Custom CSV file
    uv run manage.py import_coredata --dry-run                    # Preview changes

JSON format:
    {
        "llm_models": [
            {"model_id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B", "notes": "Good multilingual"}
        ],
        "languages": [
            {
                "code": "ja",
                "name": "Japanese",
                "primary_model": "Qwen/Qwen2.5-7B-Instruct",
                "alternative_models": ["CohereLabs/Aya-Expanse-8B"],
                "notes": "Qwen best, avoid Mistral"
            }
        ]
    }

CSV format (columns):
    ISO_Code,Language,Primary_Model,Alternative_1,Alternative_2,Notes
"""

import csv
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.core.models import Language, LLMModel


def model_id_to_name(model_id: str) -> str:
    """Convert a HuggingFace model ID to a friendly name.

    Example: "Qwen/Qwen2.5-7B-Instruct" -> "Qwen 2.5 7B Instruct"
    """
    # Take the part after the slash (or the whole string if no slash)
    name = model_id.split("/")[-1]
    # Replace hyphens and underscores with spaces
    name = name.replace("-", " ").replace("_", " ")
    # Add space before version numbers (e.g., "2.5" -> " 2.5")
    name = re.sub(r"(\d+\.?\d*)", r" \1", name)
    # Clean up multiple spaces
    name = " ".join(name.split())
    return name


class Command(BaseCommand):
    help = "Import core data (languages and LLM models) from JSON or CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/core_data.json",
            help="Path to JSON file (default: data/core_data.json)",
        )
        parser.add_argument(
            "--csv",
            type=str,
            help="Path to CSV file (overrides --file)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if options["csv"]:
            self._import_csv(options["csv"], dry_run)
        else:
            self._import_json(options["file"], dry_run)

    def _import_csv(self, file_path: str, dry_run: bool):
        """Import from CSV format."""
        path = Path(file_path)
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        self.stdout.write(f"Reading languages from CSV: {path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        # Parse CSV and collect all unique models
        models_to_create = {}  # model_id -> notes
        languages_to_create = []

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("ISO_Code") or "").strip()
                name = (row.get("Language") or "").strip()
                primary = (row.get("Primary_Model") or "").strip()
                alt1 = (row.get("Alternative_1") or "").strip()
                alt2 = (row.get("Alternative_2") or "").strip()
                notes = (row.get("Notes") or "").strip()

                if not code or not name or not primary:
                    continue

                # Collect models
                if primary and primary not in models_to_create:
                    models_to_create[primary] = ""
                if alt1 and alt1 not in models_to_create:
                    models_to_create[alt1] = ""
                if alt2 and alt2 not in models_to_create:
                    models_to_create[alt2] = ""

                alternatives = [m for m in [alt1, alt2] if m]
                languages_to_create.append(
                    {
                        "code": code,
                        "name": name,
                        "primary_model": primary,
                        "alternative_models": alternatives,
                        "notes": notes,
                    }
                )

        self._do_import(models_to_create, languages_to_create, dry_run)

    def _import_json(self, file_path: str, dry_run: bool):
        """Import from JSON format."""
        path = Path(file_path)
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        self.stdout.write(f"Reading languages from JSON: {path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Collect models from explicit list and language references
        models_to_create = {}
        for model in data.get("llm_models", []):
            model_id = model.get("model_id", "").strip()
            if model_id:
                models_to_create[model_id] = model.get("notes", "")

        languages_to_create = []
        for lang in data.get("languages", []):
            code = lang.get("code", "").strip()
            name = lang.get("name", "").strip()
            primary = lang.get("primary_model", "").strip()

            if not code or not name or not primary:
                continue

            # Also collect models referenced by languages
            if primary and primary not in models_to_create:
                models_to_create[primary] = ""
            for alt in lang.get("alternative_models", []):
                if alt and alt not in models_to_create:
                    models_to_create[alt] = ""

            languages_to_create.append(
                {
                    "code": code,
                    "name": name,
                    "primary_model": primary,
                    "alternative_models": lang.get("alternative_models", []),
                    "notes": lang.get("notes", ""),
                }
            )

        self._do_import(models_to_create, languages_to_create, dry_run)

    def _do_import(self, models_to_create: dict, languages_to_create: list, dry_run: bool):
        """Perform the actual import."""
        self.stdout.write(f"\nFound {len(models_to_create)} LLM models to import")
        self.stdout.write(f"Found {len(languages_to_create)} languages to import\n")

        if dry_run:
            self.stdout.write(self.style.MIGRATE_HEADING("LLM Models:"))
            for model_id in sorted(models_to_create.keys()):
                self.stdout.write(f"  Would create: {model_id}")

            self.stdout.write(self.style.MIGRATE_HEADING("\nLanguages:"))
            for lang in languages_to_create:
                alts = ", ".join(lang["alternative_models"]) or "none"
                self.stdout.write(
                    f"  Would create: {lang['name']} ({lang['code']}) - "
                    f"primary: {lang['primary_model']}, alternatives: {alts}"
                )
            return

        # Import within transaction
        models_created = 0
        models_updated = 0
        langs_created = 0
        langs_updated = 0

        with transaction.atomic():
            # Create/update LLM models first
            self.stdout.write(self.style.MIGRATE_HEADING("Importing LLM Models:"))
            model_objects = {}
            for model_id, notes in models_to_create.items():
                model, created = LLMModel.objects.update_or_create(
                    model_id=model_id,
                    defaults={
                        "name": model_id_to_name(model_id),
                        "notes": notes,
                        "is_active": True,
                    },
                )
                model_objects[model_id] = model
                if created:
                    models_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {model.name}"))
                else:
                    models_updated += 1
                    self.stdout.write(self.style.WARNING(f"  ~ Updated: {model.name}"))

            # Create/update languages
            self.stdout.write(self.style.MIGRATE_HEADING("\nImporting Languages:"))
            for lang_data in languages_to_create:
                primary_model = model_objects.get(lang_data["primary_model"])
                if not primary_model:
                    # Try to find existing model in database
                    primary_model = LLMModel.objects.filter(
                        model_id=lang_data["primary_model"]
                    ).first()
                if not primary_model:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ! Skipping {lang_data['code']}: "
                            f"primary model not found: {lang_data['primary_model']}"
                        )
                    )
                    continue

                lang, created = Language.objects.update_or_create(
                    code=lang_data["code"],
                    defaults={
                        "name": lang_data["name"],
                        "primary_model": primary_model,
                        "notes": lang_data["notes"],
                        "is_active": True,
                    },
                )

                # Set alternative models
                alternatives = []
                for alt_id in lang_data["alternative_models"]:
                    alt_model = model_objects.get(alt_id)
                    if not alt_model:
                        alt_model = LLMModel.objects.filter(model_id=alt_id).first()
                    if alt_model:
                        alternatives.append(alt_model)
                lang.alternative_models.set(alternatives)

                if created:
                    langs_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {lang}"))
                else:
                    langs_updated += 1
                    self.stdout.write(self.style.WARNING(f"  ~ Updated: {lang}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  LLM Models - Created: {models_created}, Updated: {models_updated}")
        self.stdout.write(f"  Languages  - Created: {langs_created}, Updated: {langs_updated}")
        self.stdout.write("=" * 60)
