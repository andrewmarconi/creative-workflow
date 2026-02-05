"""
Django management command to export adaptation markets to JSON.

Usage:
    uv run manage.py export_markets
    uv run manage.py export_markets --file data/custom_markets.json

The command exports markets in the structured JSON format:
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

If the database contains old markdown-formatted rules, they will be
automatically converted to the new structured format during export.
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.tvspots.models import AdaptationMarket


def convert_markdown_to_structured(markdown_text: str) -> list[dict]:
    """Convert old markdown rules to new structured format.

    Parses markdown with ### headings and - bullet points into:
    [{"heading": "...", "points": ["...", "..."]}]

    Also strips markdown links [text](url) from points.
    """
    # Normalize line endings
    text = markdown_text.replace("\r\n", "\n").replace("\r", "\n")

    sections = []
    current_section = None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check for heading
        if line.startswith("### "):
            if current_section:
                sections.append(current_section)
            current_section = {"heading": line[4:].strip(), "points": []}
        # Check for bullet point
        elif line.startswith("- ") and current_section:
            point = line[2:].strip()
            # Strip markdown links: [text](url) -> nothing (remove citation entirely)
            point = re.sub(r"\s*\[[^\]]+\]\([^)]+\)", "", point)
            # Remove bold markers
            point = re.sub(r"\*\*([^*]+)\*\*", r"\1", point)
            # Remove italic markers (*text*)
            point = re.sub(r"\*([^*]+)\*", r"\1", point)
            # Clean up any trailing whitespace
            point = point.strip()
            current_section["points"].append(point)

    # Don't forget the last section
    if current_section:
        sections.append(current_section)

    return sections


class Command(BaseCommand):
    help = "Export adaptation markets to data/market_profiles.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/market_profiles.json",
            help="Path to output JSON file",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        markets = AdaptationMarket.objects.filter(is_active=True).order_by("name")

        if not markets.exists():
            self.stdout.write(self.style.WARNING("No active markets found to export"))
            return

        exported_markets = []
        converted_count = 0

        for market in markets:
            rules = market.rules

            # If rules is a string (old markdown format), convert it
            if isinstance(rules, str):
                rules = convert_markdown_to_structured(rules)
                converted_count += 1

            exported_markets.append(
                {
                    "name": market.name,
                    "code": market.code,
                    "rules": rules,
                }
            )

        data = {"markets": exported_markets}

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(f"Exported {len(exported_markets)} markets to {file_path}")
        )
        for market_data in exported_markets:
            num_sections = len(market_data["rules"]) if market_data["rules"] else 0
            self.stdout.write(f"  • {market_data['name']} ({market_data['code']}) - {num_sections} sections")

        if converted_count > 0:
            self.stdout.write(
                self.style.WARNING(f"\n  Converted {converted_count} market(s) from markdown to structured format")
            )
