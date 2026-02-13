"""
Django management command to export ControlNet models to JSON file.

Exports all ControlNetModel records to data/controlnet_models.json.

Usage:
    uv run manage.py export_controlnets                    # Export to data/controlnet_models.json
    uv run manage.py export_controlnets --dir custom/      # Custom output directory
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from cw.diffusion.models import ControlNetModel


class Command(BaseCommand):
    help = "Export ControlNet model records to controlnet_models.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Output directory for JSON file (default: data/)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("=" * 60)
        self.stdout.write("Exporting ControlNet models...")
        self.stdout.write("=" * 60)

        controlnets = []
        for cn in ControlNetModel.objects.all().order_by("base_architecture", "control_type"):
            controlnets.append(
                {
                    "slug": cn.slug,
                    "label": cn.label,
                    "path": cn.path,
                    "control_type": cn.control_type,
                    "base_architecture": cn.base_architecture,
                    "default_conditioning_scale": cn.default_conditioning_scale,
                    "default_guidance_end": cn.default_guidance_end,
                    "is_active": cn.is_active,
                }
            )

        file_path = output_dir / "controlnet_models.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(controlnets, f, indent=2, ensure_ascii=False)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Export Complete!"))
        self.stdout.write(f"  Output file: {file_path.absolute()}")
        self.stdout.write(f"  ControlNet models: {len(controlnets)}")
        self.stdout.write("=" * 60)
