"""
Django management command to export core data (languages and LLM models) to JSON.

Usage:
    uv run manage.py export_coredata                      # Default: data/core_data.json
    uv run manage.py export_coredata --file backup.json   # Custom output file
    uv run manage.py export_coredata --models-only        # Export only LLM models
    uv run manage.py export_coredata --languages-only     # Export only languages

Output format:
    {
        "llm_models": [
            {"model_id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B", "notes": "..."}
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
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.core.models import Language, LLMModel


class Command(BaseCommand):
    help = "Export core data (languages and LLM models) to JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/core_data.json",
            help="Path to output JSON file (default: data/core_data.json)",
        )
        parser.add_argument(
            "--models-only",
            action="store_true",
            help="Export only LLM models",
        )
        parser.add_argument(
            "--languages-only",
            action="store_true",
            help="Export only languages",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Export only active records",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        models_only = options["models_only"]
        languages_only = options["languages_only"]
        active_only = options["active_only"]

        data = {}

        # Export LLM models
        if not languages_only:
            models_qs = LLMModel.objects.all()
            if active_only:
                models_qs = models_qs.filter(is_active=True)

            data["llm_models"] = [
                {
                    "model_id": m.model_id,
                    "name": m.name,
                    "notes": m.notes,
                    "is_active": m.is_active,
                }
                for m in models_qs.order_by("name")
            ]
            self.stdout.write(f"Exporting {len(data['llm_models'])} LLM models")

        # Export languages
        if not models_only:
            langs_qs = Language.objects.select_related("primary_model").prefetch_related(
                "alternative_models"
            )
            if active_only:
                langs_qs = langs_qs.filter(is_active=True)

            data["languages"] = [
                {
                    "code": lang.code,
                    "name": lang.name,
                    "primary_model": lang.primary_model.model_id,
                    "alternative_models": [
                        m.model_id for m in lang.alternative_models.all().order_by("name")
                    ],
                    "notes": lang.notes,
                    "is_active": lang.is_active,
                }
                for lang in langs_qs.order_by("name")
            ]
            self.stdout.write(f"Exporting {len(data['languages'])} languages")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Trailing newline

        self.stdout.write(self.style.SUCCESS(f"\nExported to: {file_path}"))
