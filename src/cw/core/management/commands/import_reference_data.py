"""
Django management command to import reference data for multi-dimensional adaptation context.

Imports:
- LLM models
- Regions with insights
- Countries with insights and default language
- Cultures
- Languages with locale codes, base_language, and insights
- M2M relationships: CountryRegion, CountryLanguage, RegionCulture

Usage:
    uv run manage.py import_reference_data                              # Default: data/reference_data.json
    uv run manage.py import_reference_data --file data/custom.json      # Custom JSON file
    uv run manage.py import_reference_data --dry-run                    # Preview changes

JSON format:
    {
        "llm_models": [{"model_id": "...", "name": "...", ...}],
        "regions": [{"code": "NA", "name": "North America", "insights": [...]}],
        "countries": [{"code": "US", "name": "United States", "default_language": "en-US", "insights": [...]}],
        "cultures": [{"code": "nordic-minimalism", "name": "...", "description": "..."}],
        "languages": [{"code": "en-US", "base_language": "en", "insights": [...]}],
        "country_regions": [{"country": "US", "region": "NA"}],
        "country_languages": [{"country": "US", "language": "en-US", "is_primary": true}],
        "region_cultures": [{"region": "NORDICS", "culture": "nordic-minimalism"}]
    }
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.core.models import (
    Country,
    CountryLanguage,
    CountryRegion,
    Culture,
    Language,
    LanguageAlternativeModel,
    LLMModel,
    Region,
    RegionCulture,
)


def model_id_to_name(model_id: str) -> str:
    """Convert a HuggingFace model ID to a friendly name.

    Example: "Qwen/Qwen2.5-7B-Instruct" -> "Qwen 2.5 7B Instruct"
    """
    name = model_id.split("/")[-1]
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r"(\d+\.?\d*)", r" \1", name)
    name = " ".join(name.split())
    return name


class Command(BaseCommand):
    help = "Import reference data (regions, countries, cultures, languages) from JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/reference_data.json",
            help="Path to JSON file (default: data/reference_data.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        file_path = options["file"]

        path = Path(file_path)
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        self.stdout.write(f"Reading reference data from: {path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract data
        llm_models_data = data.get("llm_models", [])
        regions_data = data.get("regions", [])
        countries_data = data.get("countries", [])
        cultures_data = data.get("cultures", [])
        languages_data = data.get("languages", [])
        country_regions_data = data.get("country_regions", [])
        country_languages_data = data.get("country_languages", [])
        region_cultures_data = data.get("region_cultures", [])

        # Summary
        self.stdout.write(f"\nFound {len(llm_models_data)} LLM models")
        self.stdout.write(f"Found {len(regions_data)} regions")
        self.stdout.write(f"Found {len(countries_data)} countries")
        self.stdout.write(f"Found {len(cultures_data)} cultures")
        self.stdout.write(f"Found {len(languages_data)} languages")
        self.stdout.write(f"Found {len(country_regions_data)} country-region mappings")
        self.stdout.write(f"Found {len(country_languages_data)} country-language mappings")
        self.stdout.write(f"Found {len(region_cultures_data)} region-culture mappings\n")

        if dry_run:
            self._dry_run_preview(
                llm_models_data,
                regions_data,
                countries_data,
                cultures_data,
                languages_data,
            )
            return

        # Perform import
        self._do_import(
            llm_models_data,
            regions_data,
            countries_data,
            cultures_data,
            languages_data,
            country_regions_data,
            country_languages_data,
            region_cultures_data,
        )

    def _dry_run_preview(
        self,
        llm_models_data,
        regions_data,
        countries_data,
        cultures_data,
        languages_data,
    ):
        """Preview what would be imported."""
        self.stdout.write(self.style.MIGRATE_HEADING("LLM Models:"))
        for model in llm_models_data[:5]:
            self.stdout.write(f"  Would create/update: {model.get('model_id')}")
        if len(llm_models_data) > 5:
            self.stdout.write(f"  ... and {len(llm_models_data) - 5} more")

        self.stdout.write(self.style.MIGRATE_HEADING("\nRegions:"))
        for region in regions_data:
            insights_count = len(region.get("insights", []))
            self.stdout.write(
                f"  Would create/update: {region.get('code')} - {region.get('name')} "
                f"({insights_count} insight sections)"
            )

        self.stdout.write(self.style.MIGRATE_HEADING("\nCountries:"))
        for country in countries_data:
            insights_count = len(country.get("insights", []))
            self.stdout.write(
                f"  Would create/update: {country.get('code')} - {country.get('name')} "
                f"({insights_count} insight sections)"
            )

        self.stdout.write(self.style.MIGRATE_HEADING("\nCultures:"))
        for culture in cultures_data:
            self.stdout.write(f"  Would create/update: {culture.get('code')} - {culture.get('name')}")

        self.stdout.write(self.style.MIGRATE_HEADING("\nLanguages:"))
        for lang in languages_data[:10]:
            insights_count = len(lang.get("insights", []))
            self.stdout.write(
                f"  Would create/update: {lang.get('code')} - {lang.get('name')} "
                f"(base: {lang.get('base_language')}, {insights_count} insights)"
            )
        if len(languages_data) > 10:
            self.stdout.write(f"  ... and {len(languages_data) - 10} more")

    def _do_import(
        self,
        llm_models_data,
        regions_data,
        countries_data,
        cultures_data,
        languages_data,
        country_regions_data,
        country_languages_data,
        region_cultures_data,
    ):
        """Perform the actual import within a transaction."""
        stats = {
            "llm_models_created": 0,
            "llm_models_updated": 0,
            "regions_created": 0,
            "regions_updated": 0,
            "countries_created": 0,
            "countries_updated": 0,
            "cultures_created": 0,
            "cultures_updated": 0,
            "languages_created": 0,
            "languages_updated": 0,
            "country_regions_created": 0,
            "country_languages_created": 0,
            "region_cultures_created": 0,
        }

        with transaction.atomic():
            # 1. Import LLM Models
            self.stdout.write(self.style.MIGRATE_HEADING("\n1. Importing LLM Models:"))
            model_objects = {}
            for model_data in llm_models_data:
                model_id = model_data.get("model_id", "").strip()
                if not model_id:
                    continue

                model, created = LLMModel.objects.update_or_create(
                    model_id=model_id,
                    defaults={
                        "name": model_data.get("name") or model_id_to_name(model_id),
                        "notes": model_data.get("notes", ""),
                        "is_active": model_data.get("is_active", True),
                        "load_in_4bit": model_data.get("load_in_4bit", False),
                    },
                )
                model_objects[model_id] = model
                if created:
                    stats["llm_models_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {model.name}"))
                else:
                    stats["llm_models_updated"] += 1

            # 2. Import Regions
            self.stdout.write(self.style.MIGRATE_HEADING("\n2. Importing Regions:"))
            region_objects = {}
            for region_data in regions_data:
                code = region_data.get("code", "").strip()
                if not code:
                    continue

                region, created = Region.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": region_data.get("name", ""),
                        "description": region_data.get("description", ""),
                        "insights": region_data.get("insights", []),
                        "is_active": True,
                    },
                )
                region_objects[code] = region
                if created:
                    stats["regions_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {region.name}"))
                else:
                    stats["regions_updated"] += 1

            # 3. Import Cultures
            self.stdout.write(self.style.MIGRATE_HEADING("\n3. Importing Cultures:"))
            culture_objects = {}
            for culture_data in cultures_data:
                code = culture_data.get("code", "").strip()
                if not code:
                    continue

                culture, created = Culture.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": culture_data.get("name", ""),
                        "description": culture_data.get("description", ""),
                        "is_active": True,
                    },
                )
                culture_objects[code] = culture
                if created:
                    stats["cultures_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {culture.name}"))
                else:
                    stats["cultures_updated"] += 1

            # 4. Import Languages (without default_language FKs yet)
            self.stdout.write(self.style.MIGRATE_HEADING("\n4. Importing Languages:"))
            language_objects = {}
            for lang_data in languages_data:
                code = lang_data.get("code", "").strip()
                if not code:
                    continue

                primary_model_id = lang_data.get("primary_model", "").strip()
                primary_model = model_objects.get(primary_model_id)
                if not primary_model:
                    primary_model = LLMModel.objects.filter(model_id=primary_model_id).first()
                if not primary_model:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ! Skipping {code}: primary model not found: {primary_model_id}"
                        )
                    )
                    continue

                lang, created = Language.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": lang_data.get("name", ""),
                        "base_language": lang_data.get("base_language", ""),
                        "primary_model": primary_model,
                        "insights": lang_data.get("insights", []),
                        "notes": lang_data.get("notes", ""),
                        "is_active": True,
                    },
                )
                language_objects[code] = lang

                # Set alternative models via through table
                LanguageAlternativeModel.objects.filter(language=lang).delete()
                for alt_id in lang_data.get("alternative_models", []):
                    alt_model = model_objects.get(alt_id)
                    if not alt_model:
                        alt_model = LLMModel.objects.filter(model_id=alt_id).first()
                    if alt_model:
                        LanguageAlternativeModel.objects.create(
                            language=lang, llmmodel=alt_model
                        )

                if created:
                    stats["languages_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {lang.name}"))
                else:
                    stats["languages_updated"] += 1

            # 5. Import Countries (with default_language FK now that languages exist)
            self.stdout.write(self.style.MIGRATE_HEADING("\n5. Importing Countries:"))
            country_objects = {}
            for country_data in countries_data:
                code = country_data.get("code", "").strip()
                if not code:
                    continue

                default_lang_code = country_data.get("default_language", "").strip()
                default_language = None
                if default_lang_code:
                    default_language = language_objects.get(default_lang_code)
                    if not default_language:
                        default_language = Language.objects.filter(code=default_lang_code).first()

                country, created = Country.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": country_data.get("name", ""),
                        "default_language": default_language,
                        "insights": country_data.get("insights", []),
                        "notes": country_data.get("notes", ""),
                        "is_active": True,
                    },
                )
                country_objects[code] = country
                if created:
                    stats["countries_created"] += 1
                    self.stdout.write(self.style.SUCCESS(f"  + Created: {country.name}"))
                else:
                    stats["countries_updated"] += 1

            # 6. Create M2M: Country-Region mappings
            self.stdout.write(self.style.MIGRATE_HEADING("\n6. Creating Country-Region mappings:"))
            CountryRegion.objects.all().delete()
            for mapping in country_regions_data:
                country_code = mapping.get("country")
                region_code = mapping.get("region")

                country = country_objects.get(country_code)
                region = region_objects.get(region_code)

                if not country:
                    country = Country.objects.filter(code=country_code).first()
                if not region:
                    region = Region.objects.filter(code=region_code).first()

                if country and region:
                    CountryRegion.objects.create(country=country, region=region)
                    stats["country_regions_created"] += 1
                    self.stdout.write(f"  + {country.code} → {region.code}")

            # 7. Create M2M: Country-Language mappings (with is_primary)
            self.stdout.write(self.style.MIGRATE_HEADING("\n7. Creating Country-Language mappings:"))
            CountryLanguage.objects.all().delete()
            for mapping in country_languages_data:
                country_code = mapping.get("country")
                language_code = mapping.get("language")
                is_primary = mapping.get("is_primary", False)

                country = country_objects.get(country_code)
                language = language_objects.get(language_code)

                if not country:
                    country = Country.objects.filter(code=country_code).first()
                if not language:
                    language = Language.objects.filter(code=language_code).first()

                if country and language:
                    CountryLanguage.objects.create(
                        country=country, language=language, is_primary=is_primary
                    )
                    stats["country_languages_created"] += 1
                    primary_marker = " (primary)" if is_primary else ""
                    self.stdout.write(f"  + {country.code} → {language.code}{primary_marker}")

            # 8. Create M2M: Region-Culture mappings
            self.stdout.write(self.style.MIGRATE_HEADING("\n8. Creating Region-Culture mappings:"))
            RegionCulture.objects.all().delete()
            for mapping in region_cultures_data:
                region_code = mapping.get("region")
                culture_code = mapping.get("culture")

                region = region_objects.get(region_code)
                culture = culture_objects.get(culture_code)

                if not region:
                    region = Region.objects.filter(code=region_code).first()
                if not culture:
                    culture = Culture.objects.filter(code=culture_code).first()

                if region and culture:
                    RegionCulture.objects.create(region=region, culture=culture)
                    stats["region_cultures_created"] += 1
                    self.stdout.write(f"  + {region.code} → {culture.code}")

        # Summary
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(
            f"  LLM Models - Created: {stats['llm_models_created']}, "
            f"Updated: {stats['llm_models_updated']}"
        )
        self.stdout.write(
            f"  Regions    - Created: {stats['regions_created']}, "
            f"Updated: {stats['regions_updated']}"
        )
        self.stdout.write(
            f"  Countries  - Created: {stats['countries_created']}, "
            f"Updated: {stats['countries_updated']}"
        )
        self.stdout.write(
            f"  Cultures   - Created: {stats['cultures_created']}, "
            f"Updated: {stats['cultures_updated']}"
        )
        self.stdout.write(
            f"  Languages  - Created: {stats['languages_created']}, "
            f"Updated: {stats['languages_updated']}"
        )
        self.stdout.write(f"  Country-Region mappings: {stats['country_regions_created']}")
        self.stdout.write(f"  Country-Language mappings: {stats['country_languages_created']}")
        self.stdout.write(f"  Region-Culture mappings: {stats['region_cultures_created']}")
        self.stdout.write("=" * 70)
