"""
Django management command to export reference data (regions, countries, cultures, languages, LLM models).

Exports to JSON format compatible with import_reference_data command.

Usage:
    uv run manage.py export_reference_data                              # Default: data/reference_data_export.json
    uv run manage.py export_reference_data --file data/custom.json      # Custom output file
    uv run manage.py export_reference_data --stdout                     # Print to stdout instead of file
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

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


class Command(BaseCommand):
    help = "Export reference data (regions, countries, cultures, languages, LLM models) to JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/reference_data_export.json",
            help="Path to output JSON file (default: data/reference_data_export.json)",
        )
        parser.add_argument(
            "--stdout",
            action="store_true",
            help="Print JSON to stdout instead of writing to file",
        )

    def handle(self, *args, **options):
        use_stdout = options["stdout"]
        output_file = options["file"]

        self.stdout.write("Exporting reference data...")

        # Build the data structure
        data = {
            "llm_models": self._export_llm_models(),
            "regions": self._export_regions(),
            "countries": self._export_countries(),
            "cultures": self._export_cultures(),
            "languages": self._export_languages(),
            "country_regions": self._export_country_regions(),
            "country_languages": self._export_country_languages(),
            "region_cultures": self._export_region_cultures(),
        }

        # Convert to JSON
        json_output = json.dumps(data, indent=2, ensure_ascii=False)

        if use_stdout:
            self.stdout.write(json_output)
        else:
            path = Path(output_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_output)
            self.stdout.write(self.style.SUCCESS(f"\nExported to: {path}"))

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  LLM Models: {len(data['llm_models'])}")
        self.stdout.write(f"  Regions: {len(data['regions'])}")
        self.stdout.write(f"  Countries: {len(data['countries'])}")
        self.stdout.write(f"  Cultures: {len(data['cultures'])}")
        self.stdout.write(f"  Languages: {len(data['languages'])}")
        self.stdout.write(f"  Country-Region mappings: {len(data['country_regions'])}")
        self.stdout.write(f"  Country-Language mappings: {len(data['country_languages'])}")
        self.stdout.write(f"  Region-Culture mappings: {len(data['region_cultures'])}")
        self.stdout.write("=" * 60)

    def _export_llm_models(self):
        """Export all LLM models."""
        models = []
        for model in LLMModel.objects.all().order_by("model_id"):
            models.append(
                {
                    "model_id": model.model_id,
                    "name": model.name,
                    "notes": model.notes,
                    "is_active": model.is_active,
                    "load_in_4bit": model.load_in_4bit,
                }
            )
        return models

    def _export_regions(self):
        """Export all regions with insights."""
        regions = []
        for region in Region.objects.all().order_by("code"):
            regions.append(
                {
                    "code": region.code,
                    "name": region.name,
                    "description": region.description,
                    "insights": region.insights,
                    "is_active": region.is_active,
                }
            )
        return regions

    def _export_countries(self):
        """Export all countries with insights."""
        countries = []
        for country in Country.objects.all().order_by("code"):
            countries.append(
                {
                    "code": country.code,
                    "name": country.name,
                    "default_language": country.default_language.code if country.default_language else None,
                    "insights": country.insights,
                    "notes": country.notes,
                    "is_active": country.is_active,
                }
            )
        return countries

    def _export_cultures(self):
        """Export all cultures."""
        cultures = []
        for culture in Culture.objects.all().order_by("code"):
            cultures.append(
                {
                    "code": culture.code,
                    "name": culture.name,
                    "description": culture.description,
                    "is_active": culture.is_active,
                }
            )
        return cultures

    def _export_languages(self):
        """Export all languages with insights and model references."""
        languages = []
        for lang in Language.objects.all().order_by("code"):
            # Get alternative models
            alternative_models = [
                am.llmmodel.model_id
                for am in LanguageAlternativeModel.objects.filter(language=lang).select_related("llmmodel")
            ]

            languages.append(
                {
                    "code": lang.code,
                    "name": lang.name,
                    "base_language": lang.base_language,
                    "primary_model": lang.primary_model.model_id,
                    "alternative_models": alternative_models,
                    "insights": lang.insights,
                    "notes": lang.notes,
                    "is_active": lang.is_active,
                }
            )
        return languages

    def _export_country_regions(self):
        """Export country-region mappings."""
        mappings = []
        for cr in CountryRegion.objects.all().select_related("country", "region"):
            mappings.append(
                {
                    "country_code": cr.country.code,
                    "region_code": cr.region.code,
                }
            )
        return mappings

    def _export_country_languages(self):
        """Export country-language mappings."""
        mappings = []
        for cl in CountryLanguage.objects.all().select_related("country", "language"):
            mappings.append(
                {
                    "country_code": cl.country.code,
                    "language_code": cl.language.code,
                    "is_primary": cl.is_primary,
                }
            )
        return mappings

    def _export_region_cultures(self):
        """Export region-culture mappings."""
        mappings = []
        for rc in RegionCulture.objects.all().select_related("region", "culture"):
            mappings.append(
                {
                    "region_code": rc.region.code,
                    "culture_code": rc.culture.code,
                }
            )
        return mappings
