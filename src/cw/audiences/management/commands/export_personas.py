"""
Django management command to export Personas to JSON files.

Exports Persona records and their segment associations to separate JSON files:
- data/personas.json (persona data with geographic references)
- data/persona_segments.json (M2M mappings with order_index)

Usage:
    uv run manage.py export_personas                    # Export to data/ directory
    uv run manage.py export_personas --dir custom/      # Custom output directory
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.audiences.models import Persona, PersonaSegment


class Command(BaseCommand):
    help = "Export Persona records to personas.json and persona_segments.json"

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
        self.stdout.write("Exporting personas...")
        self.stdout.write("=" * 60)

        # Export personas
        personas = []
        for persona in Persona.objects.all().order_by("name"):
            personas.append(
                {
                    "name": persona.name,
                    "description": persona.description,
                    "region_code": persona.region.code if persona.region else None,
                    "country_code": persona.country.code if persona.country else None,
                    "language_code": persona.language.code if persona.language else None,
                    "is_active": persona.is_active,
                }
            )

        personas_file = output_dir / "personas.json"
        with open(personas_file, "w", encoding="utf-8") as f:
            json.dump(personas, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(personas)} personas")

        # Export persona-segment mappings
        mappings = []
        for ps in PersonaSegment.objects.all().select_related("persona", "segment").order_by("persona__name", "order_index"):
            mappings.append(
                {
                    "persona_name": ps.persona.name,
                    "segment_category": ps.segment.category,
                    "segment_vector": ps.segment.vector,
                    "segment_value": ps.segment.value,
                    "order_index": ps.order_index,
                }
            )

        mappings_file = output_dir / "persona_segments.json"
        with open(mappings_file, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)

        self.stdout.write(f"  ✓ Exported {len(mappings)} persona-segment mappings")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Output directory: {output_dir.absolute()}")
        self.stdout.write(f"  Personas: {len(personas)} → personas.json")
        self.stdout.write(f"  Persona-Segment mappings: {len(mappings)} → persona_segments.json")
        self.stdout.write("=" * 60)
