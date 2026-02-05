"""
Django management command to import adaptations.json into prompts and jobs.

Usage:
    python manage.py import_adaptations
    python manage.py import_adaptations --file path/to/adaptations.json
    python manage.py import_adaptations --dry-run
"""

import json
import os
from pathlib import Path

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cw.diffusion.models import DiffusionJob, DiffusionModel, LoraModel, Prompt


class Command(BaseCommand):
    help = "Import adaptations.json into prompts and generate diffusion jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/adaptations.json",
            help="Path to adaptations.json file (default: data/adaptations.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating anything",
        )

    def _get_or_create_lora(self, lora_settings, base_architecture):
        """
        Get or create a LoRA from settings. If AIR is provided and LoRA doesn't exist,
        fetch metadata from CivitAI and create it.

        Args:
            lora_settings: Dict with 'air' and optionally 'path', 'strength'
            base_architecture: Base architecture of the model (for compatibility)

        Returns:
            LoraModel instance or None
        """
        air = lora_settings.get("air")
        path = lora_settings.get("path")

        if not air and not path:
            return None

        # Try to find existing LoRA by AIR first, then path
        lora = None
        if air:
            lora = LoraModel.objects.filter(air=air).first()
        if not lora and path:
            lora = LoraModel.objects.filter(path=path).first()

        if lora:
            self.stdout.write(f"  Found existing LoRA: {lora.label}")
            return lora

        # LoRA doesn't exist - fetch from CivitAI if we have AIR
        if not air:
            raise CommandError(f"LoRA path '{path}' not found and no AIR provided for auto-fetch")

        self.stdout.write(self.style.WARNING(f"  LoRA not found, fetching from CivitAI..."))

        # Import CivitAI utilities
        from lib.civitai import (
            extract_lora_metadata,
            fetch_model_version_metadata,
            parse_air,
        )

        # Get API key
        api_key = os.environ.get("CIVITAI_API_KEY")

        try:
            # Parse AIR and fetch metadata
            model_id, version_id = parse_air(air)
            metadata = fetch_model_version_metadata(version_id, api_key)
            extracted = extract_lora_metadata(metadata)

            # Create LoRA record
            lora = LoraModel.objects.create(
                label=extracted["label"],
                air=air,
                path="",  # Will be downloaded on first use
                base_architecture=extracted["base_architecture"],
                prompt_suffix=extracted.get("prompt_suffix", ""),
                negative_prompt_suffix=extracted.get("negative_prompt_suffix", ""),
                default_strength=lora_settings.get("strength", 0.8),
                guidance_scale=extracted.get("guidance_scale"),
                notes=extracted.get("notes", ""),
                is_active=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Created LoRA: {lora.label} (arch: {lora.base_architecture})"
                )
            )

            # Warn if architecture mismatch
            if lora.base_architecture != base_architecture:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ⚠ Architecture mismatch: LoRA is {lora.base_architecture}, "
                        f"model is {base_architecture}"
                    )
                )

            return lora

        except Exception as e:
            raise CommandError(f"Failed to fetch LoRA from CivitAI: {e}")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        dry_run = options["dry_run"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        self.stdout.write(f"Reading adaptations from: {file_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        # Load adaptations
        with open(file_path, "r") as f:
            data = json.load(f)

        settings = data.get("settings", {})
        prompts_data = data.get("prompts", [])

        if not prompts_data:
            raise CommandError("No prompts found in adaptations file")

        # Get the model by slug
        model_slug = settings.get("model")
        if not model_slug:
            raise CommandError("No 'model' specified in settings")

        try:
            diffusion_model = DiffusionModel.objects.get(slug=model_slug)
        except DiffusionModel.DoesNotExist:
            raise CommandError(f"Model not found: {model_slug}")

        self.stdout.write(f"\nUsing model: {diffusion_model.label} ({model_slug})")
        self.stdout.write(f"Settings:")
        self.stdout.write(f"  Width: {settings.get('width', 'default')}")
        self.stdout.write(f"  Height: {settings.get('height', 'default')}")
        self.stdout.write(f"  Guidance Scale: {settings.get('guidance_scale', 'default')}")
        self.stdout.write(f"  Scheduler: {settings.get('scheduler', 'default')}")

        # Handle LoRA settings
        lora_settings = settings.get("lora")
        lora_model = None
        lora_strength = None

        if lora_settings:
            lora_air = lora_settings.get("air", "")
            lora_strength = lora_settings.get("strength")
            self.stdout.write(f"  LoRA AIR: {lora_air}")
            if lora_strength:
                self.stdout.write(f"  LoRA Strength: {lora_strength}")

        self.stdout.write(f"\nPrompts to import: {len(prompts_data)}")

        if dry_run:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("Would create the following:")
            if lora_settings:
                self.stdout.write(
                    f"  LoRA: {lora_settings.get('air', lora_settings.get('path', 'unknown'))}"
                )
            for prompt_data in prompts_data:
                identifier = prompt_data.get("indentifier") or prompt_data.get("identifier", "")
                source = prompt_data.get("source_prompt", "")[:80]
                self.stdout.write(f"  [{identifier}] {source}...")
            self.stdout.write("=" * 60)
            return

        # Get or create LoRA if specified
        if lora_settings:
            lora_model = self._get_or_create_lora(lora_settings, diffusion_model.base_architecture)

        # Import within transaction
        prompts_created = 0
        jobs_created = 0

        with transaction.atomic():
            self.stdout.write("\nCreating prompts and jobs:")

            for prompt_data in prompts_data:
                identifier = prompt_data.get("indentifier") or prompt_data.get("identifier", "")
                source_prompt = prompt_data.get("source_prompt", "")

                if not source_prompt:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Skipping {identifier}: no source_prompt")
                    )
                    continue

                # Create Prompt
                prompt = Prompt.objects.create(
                    source_prompt=source_prompt,
                    enhancement_method="none",
                )
                prompts_created += 1

                # Create DiffusionJob with settings
                job = DiffusionJob.objects.create(
                    diffusion_model=diffusion_model,
                    lora_model=lora_model,
                    prompt=prompt,
                    identifier=identifier,
                    width=settings.get("width"),
                    height=settings.get("height"),
                    guidance_scale=settings.get("guidance_scale"),
                    scheduler=settings.get("scheduler", ""),
                    lora_strength=lora_strength,
                )
                jobs_created += 1

                lora_info = f" + {lora_model.label}" if lora_model else ""
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ [{identifier}] Job #{job.pk}{lora_info}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Prompts created: {prompts_created}")
        self.stdout.write(f"  Jobs created: {jobs_created}")
        if lora_model:
            self.stdout.write(f"  LoRA: {lora_model.label}")
        self.stdout.write("=" * 60)
