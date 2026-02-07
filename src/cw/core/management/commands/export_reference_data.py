"""
Django management command to export reference data to separate JSON files per model.

Exports each model type to its own file in the data/ directory:
- data/llm_models.json
- data/regions.json
- data/countries.json
- data/languages.json
- data/country_regions.json
- data/country_languages.json

Usage:
    uv run manage.py export_reference_data                    # Export to data/ directory
    uv run manage.py export_reference_data --dir custom/       # Custom output directory
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

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
    help = "Export reference data to separate JSON files per model type"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Output directory for JSON files (default: data/)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("=" * 60)
        self.stdout.write("Exporting reference data to separate files...")
        self.stdout.write("=" * 60)

        # Export each model type to its own file
        stats = {}

        stats["llm_models"] = self._export_llm_models(output_dir)
        stats["regions"] = self._export_regions(output_dir)
        stats["countries"] = self._export_countries(output_dir)
        stats["languages"] = self._export_languages(output_dir)
        stats["country_regions"] = self._export_country_regions(output_dir)
        stats["country_languages"] = self._export_country_languages(output_dir)

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Output directory: {output_dir.absolute()}")
        self.stdout.write(f"  LLM Models: {stats['llm_models']} → llm_models.json")
        self.stdout.write(f"  Regions: {stats['regions']} → regions.json")
        self.stdout.write(f"  Countries: {stats['countries']} → countries.json")
        self.stdout.write(f"  Languages: {stats['languages']} → languages.json")
        self.stdout.write(f"  Country-Region mappings: {stats['country_regions']} → country_regions.json")
        self.stdout.write(f"  Country-Language mappings: {stats['country_languages']} → country_languages.json")
        self.stdout.write("=" * 60)

    def _export_llm_models(self, output_dir: Path) -> int:
        """Export LLM models to llm_models.json."""
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

        file_path = output_dir / "llm_models.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(models, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(models)} LLM models")
        return len(models)

    def _export_regions(self, output_dir: Path) -> int:
        """Export regions to regions.json."""
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

        file_path = output_dir / "regions.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(regions, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(regions)} regions")
        return len(regions)

    def _export_countries(self, output_dir: Path) -> int:
        """Export countries to countries.json."""
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

        file_path = output_dir / "countries.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(countries, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(countries)} countries")
        return len(countries)

    def _export_languages(self, output_dir: Path) -> int:
        """Export languages with model references to languages.json."""
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

        file_path = output_dir / "languages.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(languages, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(languages)} languages")
        return len(languages)

    def _export_country_regions(self, output_dir: Path) -> int:
        """Export country-region mappings to country_regions.json."""
        mappings = []
        for cr in CountryRegion.objects.all().select_related("country", "region"):
            mappings.append(
                {
                    "country_code": cr.country.code,
                    "region_code": cr.region.code,
                }
            )

        file_path = output_dir / "country_regions.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(mappings)} country-region mappings")
        return len(mappings)

    def _export_country_languages(self, output_dir: Path) -> int:
        """Export country-language mappings to country_languages.json."""
        mappings = []
        for cl in CountryLanguage.objects.all().select_related("country", "language"):
            mappings.append(
                {
                    "country_code": cl.country.code,
                    "language_code": cl.language.code,
                    "is_primary": cl.is_primary,
                }
            )

        file_path = output_dir / "country_languages.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(mappings)} country-language mappings")
        return len(mappings)
