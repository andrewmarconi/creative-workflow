"""
Django management command to import reference data from separate JSON files.

Reads each model type from its own file in the data/ directory:
- data/llm_models.json
- data/regions.json
- data/countries.json
- data/languages.json
- data/country_regions.json
- data/country_languages.json

Handles relationships via codes/IDs (e.g., languages reference primary_model by model_id).

Usage:
    uv run manage.py import_reference_data                        # Import from data/ directory
    uv run manage.py import_reference_data --dir custom/           # Custom input directory
    uv run manage.py import_reference_data --dry-run               # Preview without importing
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.core.models import (
    Country,
    CountryLanguage,
    CountryRegion,
    Language,
    LanguageAlternativeModel,
    LLMModel,
    Region,
)


class Command(BaseCommand):
    help = "Import reference data from separate JSON files per model type"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Input directory containing JSON files (default: data/)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying database",
        )

    def handle(self, *args, **options):
        input_dir = Path(options["dir"])
        is_dry_run = options["dry_run"]

        # Load all data files
        self.stdout.write("=" * 60)
        self.stdout.write("Loading reference data from separate files...")
        self.stdout.write("=" * 60)

        try:
            data = self._load_all_files(input_dir)
        except FileNotFoundError as e:
            raise CommandError(f"Missing required file: {e}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        # Preview or import
        if is_dry_run:
            self._dry_run_preview(data)
        else:
            self._do_import(data)

    def _load_all_files(self, input_dir: Path) -> dict:
        """Load all JSON files and return data dictionary."""
        data = {}

        files = {
            "llm_models": "llm_models.json",
            "regions": "regions.json",
            "countries": "countries.json",
            "languages": "languages.json",
            "country_regions": "country_regions.json",
            "country_languages": "country_languages.json",
        }

        for key, filename in files.items():
            file_path = input_dir / filename
            if not file_path.exists():
                raise FileNotFoundError(f"{filename}")

            with open(file_path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)

            self.stdout.write(f"  ✓ Loaded {filename}: {len(data[key])} records")

        return data

    def _dry_run_preview(self, data: dict):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nLLM Models:")
        for item in data["llm_models"][:3]:
            self.stdout.write(f"  - {item['model_id']}: {item['name']}")
        if len(data["llm_models"]) > 3:
            self.stdout.write(f"  ... and {len(data['llm_models']) - 3} more")

        self.stdout.write("\nRegions:")
        for item in data["regions"][:3]:
            self.stdout.write(f"  - {item['code']}: {item['name']}")
        if len(data["regions"]) > 3:
            self.stdout.write(f"  ... and {len(data['regions']) - 3} more")

        self.stdout.write("\nCountries:")
        for item in data["countries"][:3]:
            self.stdout.write(f"  - {item['code']}: {item['name']}")
        if len(data["countries"]) > 3:
            self.stdout.write(f"  ... and {len(data['countries']) - 3} more")

        self.stdout.write("\nLanguages:")
        for item in data["languages"][:3]:
            self.stdout.write(f"  - {item['code']}: {item['name']} (primary_model: {item['primary_model']})")
        if len(data["languages"]) > 3:
            self.stdout.write(f"  ... and {len(data['languages']) - 3} more")

        self.stdout.write(f"\nCountry-Region mappings: {len(data['country_regions'])}")
        self.stdout.write(f"Country-Language mappings: {len(data['country_languages'])}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, data: dict):
        """Import all data in dependency order within a transaction."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing reference data...")
        self.stdout.write("=" * 60)

        stats = {
            "llm_models_created": 0,
            "llm_models_updated": 0,
            "regions_created": 0,
            "regions_updated": 0,
            "countries_created": 0,
            "countries_updated": 0,
            "languages_created": 0,
            "languages_updated": 0,
            "country_regions_created": 0,
            "country_languages_created": 0,
        }

        # Import in dependency order
        self.stdout.write("\n1. Importing LLM Models...")
        for item in data["llm_models"]:
            obj, created = LLMModel.objects.update_or_create(
                model_id=item["model_id"],
                defaults={
                    "name": item["name"],
                    "notes": item.get("notes", ""),
                    "is_active": item.get("is_active", True),
                    "load_in_4bit": item.get("load_in_4bit", False),
                },
            )
            if created:
                stats["llm_models_created"] += 1
            else:
                stats["llm_models_updated"] += 1
        self.stdout.write(f"  ✓ Created: {stats['llm_models_created']}, Updated: {stats['llm_models_updated']}")

        self.stdout.write("\n2. Importing Regions...")
        for item in data["regions"]:
            obj, created = Region.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "insights": item.get("insights", {}),
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                stats["regions_created"] += 1
            else:
                stats["regions_updated"] += 1
        self.stdout.write(f"  ✓ Created: {stats['regions_created']}, Updated: {stats['regions_updated']}")

        self.stdout.write("\n3. Importing Languages...")
        for item in data["languages"]:
            # Resolve primary_model FK
            try:
                primary_model = LLMModel.objects.get(model_id=item["primary_model"])
            except LLMModel.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  Error: LLM Model {item['primary_model']} not found for language {item['code']}")
                )
                continue

            obj, created = Language.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "base_language": item.get("base_language", ""),
                    "primary_model": primary_model,
                    "insights": item.get("insights", {}),
                    "notes": item.get("notes", ""),
                    "is_active": item.get("is_active", True),
                },
            )

            # Handle alternative models (clear and recreate)
            LanguageAlternativeModel.objects.filter(language=obj).delete()
            for model_id in item.get("alternative_models", []):
                try:
                    alt_model = LLMModel.objects.get(model_id=model_id)
                    LanguageAlternativeModel.objects.create(language=obj, llmmodel=alt_model)
                except LLMModel.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  Warning: Alternative model {model_id} not found for language {item['code']}")
                    )

            if created:
                stats["languages_created"] += 1
            else:
                stats["languages_updated"] += 1
        self.stdout.write(f"  ✓ Created: {stats['languages_created']}, Updated: {stats['languages_updated']}")

        self.stdout.write("\n4. Importing Countries...")
        for item in data["countries"]:
            # Resolve default_language FK
            default_language = None
            if item.get("default_language"):
                try:
                    default_language = Language.objects.get(code=item["default_language"])
                except Language.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Warning: Language {item['default_language']} not found for country {item['code']}"
                        )
                    )

            obj, created = Country.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "default_language": default_language,
                    "insights": item.get("insights", {}),
                    "notes": item.get("notes", ""),
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                stats["countries_created"] += 1
            else:
                stats["countries_updated"] += 1
        self.stdout.write(f"  ✓ Created: {stats['countries_created']}, Updated: {stats['countries_updated']}")

        self.stdout.write("\n5. Creating Country-Region mappings...")
        # Clear existing mappings and recreate
        CountryRegion.objects.all().delete()
        for item in data["country_regions"]:
            try:
                country = Country.objects.get(code=item["country_code"])
                region = Region.objects.get(code=item["region_code"])
                CountryRegion.objects.create(country=country, region=region)
                stats["country_regions_created"] += 1
            except (Country.DoesNotExist, Region.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: Skipping mapping {item['country_code']} → {item['region_code']}: {e}")
                )
        self.stdout.write(f"  ✓ Created: {stats['country_regions_created']}")

        self.stdout.write("\n6. Creating Country-Language mappings...")
        # Clear existing mappings and recreate
        CountryLanguage.objects.all().delete()
        for item in data["country_languages"]:
            try:
                country = Country.objects.get(code=item["country_code"])
                language = Language.objects.get(code=item["language_code"])
                CountryLanguage.objects.create(
                    country=country,
                    language=language,
                    is_primary=item.get("is_primary", False),
                )
                stats["country_languages_created"] += 1
            except (Country.DoesNotExist, Language.DoesNotExist) as e:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: Skipping mapping {item['country_code']} → {item['language_code']}: {e}")
                )
        self.stdout.write(f"  ✓ Created: {stats['country_languages_created']}")

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  LLM Models: {stats['llm_models_created']} created, {stats['llm_models_updated']} updated")
        self.stdout.write(f"  Regions: {stats['regions_created']} created, {stats['regions_updated']} updated")
        self.stdout.write(f"  Countries: {stats['countries_created']} created, {stats['countries_updated']} updated")
        self.stdout.write(f"  Languages: {stats['languages_created']} created, {stats['languages_updated']} updated")
        self.stdout.write(f"  Country-Region mappings: {stats['country_regions_created']} created")
        self.stdout.write(f"  Country-Language mappings: {stats['country_languages_created']} created")
        self.stdout.write("=" * 60)
