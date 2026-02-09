"""
Django management command to import Personas from JSON files.

Reads Persona records and their segment associations from separate JSON files:
- data/personas.json (persona data with geographic references)
- data/persona_segments.json (M2M mappings with order_index)

Handles relationships via codes (e.g., personas reference region_code, country_code, language_code).

Usage:
    uv run manage.py import_personas                        # Import from data/ directory
    uv run manage.py import_personas --dir custom/          # Custom input directory
    uv run manage.py import_personas --dry-run              # Preview without importing
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.audiences.models import Country, Language, Persona, PersonaSegment, Region, Segment


class Command(BaseCommand):
    help = "Import Persona records from personas.json and persona_segments.json"

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

        # Load data files
        self.stdout.write("=" * 60)
        self.stdout.write("Loading personas...")
        self.stdout.write("=" * 60)

        try:
            data = self._load_files(input_dir)
        except FileNotFoundError as e:
            raise CommandError(f"Missing required file: {e}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        # Preview or import
        if is_dry_run:
            self._dry_run_preview(data)
        else:
            self._do_import(data)

    def _load_files(self, input_dir: Path) -> dict:
        """Load all JSON files and return data dictionary."""
        data = {}

        # Load personas
        personas_file = input_dir / "personas.json"
        if not personas_file.exists():
            raise FileNotFoundError("personas.json")

        with open(personas_file, "r", encoding="utf-8") as f:
            try:
                data["personas"] = json.load(f)
            except json.JSONDecodeError:
                # Handle empty or invalid files as empty arrays
                self.stdout.write(self.style.WARNING(f"  Warning: {personas_file.name} is empty or invalid, treating as empty array"))
                data["personas"] = []
        self.stdout.write(f"  ✓ Loaded personas.json: {len(data['personas'])} records")

        # Load persona-segment mappings
        mappings_file = input_dir / "persona_segments.json"
        if not mappings_file.exists():
            raise FileNotFoundError("persona_segments.json")

        with open(mappings_file, "r", encoding="utf-8") as f:
            try:
                data["persona_segments"] = json.load(f)
            except json.JSONDecodeError:
                # Handle empty or invalid files as empty arrays
                self.stdout.write(self.style.WARNING(f"  Warning: {mappings_file.name} is empty or invalid, treating as empty array"))
                data["persona_segments"] = []
        self.stdout.write(f"  ✓ Loaded persona_segments.json: {len(data['persona_segments'])} records")

        return data

    def _dry_run_preview(self, data: dict):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nPersonas to import:")
        for item in data["personas"][:5]:
            geo_parts = []
            if item.get("region_code"):
                geo_parts.append(item["region_code"])
            if item.get("country_code"):
                geo_parts.append(item["country_code"])
            if item.get("language_code"):
                geo_parts.append(item["language_code"])
            geo_str = f" ({'/'.join(geo_parts)})" if geo_parts else ""
            self.stdout.write(f"  - {item['name']}{geo_str}")
        if len(data["personas"]) > 5:
            self.stdout.write(f"  ... and {len(data['personas']) - 5} more")

        self.stdout.write(f"\nPersona-Segment mappings: {len(data['persona_segments'])}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, data: dict):
        """Import all data in dependency order within a transaction."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing personas...")
        self.stdout.write("=" * 60)

        stats = {
            "personas_created": 0,
            "personas_updated": 0,
            "persona_segments_created": 0,
        }

        # Import personas
        self.stdout.write("\n1. Importing Personas...")
        for item in data["personas"]:
            # Resolve geographic FK references
            region = None
            if item.get("region_code"):
                try:
                    region = Region.objects.get(code=item["region_code"])
                except Region.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  Warning: Region {item['region_code']} not found for persona {item['name']}")
                    )

            country = None
            if item.get("country_code"):
                try:
                    country = Country.objects.get(code=item["country_code"])
                except Country.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  Warning: Country {item['country_code']} not found for persona {item['name']}")
                    )

            language = None
            if item.get("language_code"):
                try:
                    language = Language.objects.get(code=item["language_code"])
                except Language.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  Warning: Language {item['language_code']} not found for persona {item['name']}")
                    )

            obj, created = Persona.objects.update_or_create(
                name=item["name"],
                defaults={
                    "description": item.get("description", ""),
                    "region": region,
                    "country": country,
                    "language": language,
                    "is_active": item.get("is_active", True),
                },
            )
            if created:
                stats["personas_created"] += 1
            else:
                stats["personas_updated"] += 1

        self.stdout.write(f"  ✓ Created: {stats['personas_created']}, Updated: {stats['personas_updated']}")

        # Import persona-segment mappings
        self.stdout.write("\n2. Creating Persona-Segment mappings...")
        # Clear existing mappings and recreate
        PersonaSegment.objects.all().delete()
        for item in data["persona_segments"]:
            try:
                persona = Persona.objects.get(name=item["persona_name"])
                segment = Segment.objects.get(
                    category=item["segment_category"],
                    vector=item["segment_vector"],
                    value=item["segment_value"],
                )
                PersonaSegment.objects.create(
                    persona=persona,
                    segment=segment,
                    order_index=item.get("order_index", 0),
                )
                stats["persona_segments_created"] += 1
            except Persona.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: Persona {item['persona_name']} not found, skipping mapping")
                )
            except Segment.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Warning: Segment {item['segment_category']}: {item['segment_vector']} → {item['segment_value']} not found"
                    )
                )

        self.stdout.write(f"  ✓ Created: {stats['persona_segments_created']}")

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Personas: {stats['personas_created']} created, {stats['personas_updated']} updated")
        self.stdout.write(f"  Persona-Segment mappings: {stats['persona_segments_created']} created")
        self.stdout.write("=" * 60)
