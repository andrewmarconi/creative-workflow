"""
Django management command to import adaptation markets from JSON.

Usage:
    uv run manage.py import_markets
    uv run manage.py import_markets --file data/custom_markets.json
    uv run manage.py import_markets --dry-run

Expected JSON format (structured rules):
    {
        "markets": [
            {
                "name": "France",
                "code": "fr",
                "rules": [
                    {"heading": "Language segmentation", "points": ["...", "..."]},
                    {"heading": "Tone and register", "points": ["..."]}
                ]
            }
        ]
    }

The command validates the rules structure before importing.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.tvspots.models import AdaptationMarket


def validate_rules_structure(rules: list) -> list[str]:
    """Validate that rules follow the expected structure.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    if not isinstance(rules, list):
        errors.append(f"rules must be a list, got {type(rules).__name__}")
        return errors

    for i, section in enumerate(rules):
        if not isinstance(section, dict):
            errors.append(f"rules[{i}] must be a dict, got {type(section).__name__}")
            continue

        if "heading" not in section:
            errors.append(f"rules[{i}] missing required 'heading' field")

        if "points" not in section:
            errors.append(f"rules[{i}] missing required 'points' field")
        elif not isinstance(section.get("points"), list):
            errors.append(f"rules[{i}].points must be a list")
        else:
            for j, point in enumerate(section["points"]):
                if not isinstance(point, str):
                    errors.append(f"rules[{i}].points[{j}] must be a string")

    return errors


class Command(BaseCommand):
    help = "Import adaptation markets from data/market_profiles.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/market_profiles.json",
            help="Path to market profiles JSON file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        dry_run = options["dry_run"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading markets from: {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        # Parse JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "markets" not in data:
            raise CommandError("JSON file must have a 'markets' key")

        markets = []
        for market in data["markets"]:
            if not all(k in market for k in ("name", "code", "rules")):
                raise CommandError(f"Market missing required fields: {market}")

            # Validate the rules structure
            rules = market["rules"]
            validation_errors = validate_rules_structure(rules)
            if validation_errors:
                raise CommandError(
                    f"Invalid rules structure for market '{market['name']}':\n"
                    + "\n".join(f"  - {e}" for e in validation_errors)
                )

            markets.append(
                {
                    "name": market["name"],
                    "code": market["code"],
                    "rules": rules,
                }
            )

        if not markets:
            raise CommandError("No markets found in file")

        self.stdout.write(f"Found {len(markets)} markets to import\n")

        if dry_run:
            for market in markets:
                num_sections = len(market["rules"]) if market["rules"] else 0
                self.stdout.write(
                    f"  Would create: {market['name']} ({market['code']}) - {num_sections} sections"
                )
            return

        # Import within transaction
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for market_data in markets:
                market, created = AdaptationMarket.objects.update_or_create(
                    code=market_data["code"],
                    defaults={
                        "name": market_data["name"],
                        "rules": market_data["rules"],
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {market.name}"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"  ↻ Updated: {market.name}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write("=" * 60)
