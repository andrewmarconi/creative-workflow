"""
Django management command to preload/download diffusion models.

Downloads and caches all models from HuggingFace Hub to
~/.cache/huggingface/ for offline availability.

Usage:
    uv run manage.py preload_models
    uv run manage.py preload_models --model zimageturbo
    uv run manage.py preload_models --list
"""

import sys
from pathlib import Path

import torch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cw.diffusion.models import DiffusionModel

# Add lib/ to path for ModelFactory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent / "lib"))

from models import ModelFactory


class Command(BaseCommand):
    help = "Download and cache diffusion models from HuggingFace Hub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            help="Model slug to preload (if not specified, loads all active models)",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available models and exit",
        )

    def _get_device(self):
        if torch.backends.mps.is_available():
            return torch.device("mps")
        elif torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def _resolve_model_path(self, path):
        """Resolve model path: HuggingFace ID or local path."""
        if path.startswith("Hugginface:") or path.startswith("Huggingface:"):
            return path.split(":", 1)[1]
        if "/" in path and not path.endswith(".safetensors"):
            return path
        return str(settings.MODEL_BASE_PATH / path)

    def _db_model_to_config(self, db_model):
        """Convert a DiffusionModel DB record to a presets-style config dict."""
        return {
            "label": db_model.label,
            "slug": db_model.slug,
            "path": db_model.path,
            "pipeline": db_model.pipeline,
            "settings": {
                "steps": db_model.steps,
                "guidance_scale": float(db_model.guidance_scale),
                "default_width": db_model.default_width,
                "default_height": db_model.default_height,
                "scheduler": db_model.scheduler,
                "dtype": db_model.dtype,
                "supports_negative_prompt": db_model.supports_negative_prompt,
                "max_sequence_length": db_model.max_sequence_length,
            },
        }

    def handle(self, *args, **options):
        device = self._get_device()
        models = DiffusionModel.objects.filter(is_active=True)

        if options["list"]:
            self.stdout.write("Available models:")
            for m in models:
                self.stdout.write(f"  {m.slug}: {m.label}")
            return

        if options["model"]:
            try:
                models = [models.get(slug=options["model"])]
            except DiffusionModel.DoesNotExist:
                raise CommandError(
                    f"Model '{options['model']}' not found. "
                    f"Run with --list to see available models."
                )

        total = len(models)
        self.stdout.write("=" * 60)
        self.stdout.write("Creative Workflow - Model Preloader")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Models to download: {total}")
        self.stdout.write(f"Device: {device}")
        self.stdout.write(f"Cache: ~/.cache/huggingface/")
        self.stdout.write("=" * 60)

        succeeded = 0
        failed = 0

        for i, db_model in enumerate(models, 1):
            self.stdout.write(f"\n[{i}/{total}] Loading: {db_model.label}")
            self.stdout.write(f"Slug: {db_model.slug}")
            self.stdout.write("-" * 60)

            model_config = self._db_model_to_config(db_model)
            model_path = self._resolve_model_path(db_model.path)
            self.stdout.write(f"Path: {model_path}")

            try:

                def progress_callback(progress, desc):
                    percentage = int(progress * 100)
                    self.stdout.write(f"  [{percentage:3d}%] {desc}")

                model = ModelFactory.create_model(model_config, model_path)
                status = model.load_pipeline(progress_callback=progress_callback)

                if not model.is_loaded():
                    raise RuntimeError(f"Failed to load model: {status}")

                self.stdout.write(self.style.SUCCESS(f"  {db_model.label} loaded successfully!"))
                succeeded += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error loading {db_model.label}: {e}"))
                failed += 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Preloading complete!"))
        self.stdout.write(f"  Succeeded: {succeeded}")
        if failed:
            self.stdout.write(self.style.ERROR(f"  Failed: {failed}"))
        self.stdout.write("=" * 60)
