#!/usr/bin/env python3
"""
Generative Creative Lab - Model Preloader
Downloads and caches all models from HuggingFace Hub

This script pre-downloads all models configured in presets.json to the
HuggingFace cache directory (~/.cache/huggingface/). Useful for:
- Initial setup on new machines
- Ensuring offline availability
- Avoiding download delays during first use

Usage:
    python preloader.py                 # Load all models
    python preloader.py --model zimageturbo  # Load specific model by slug
"""

import argparse
import logging
import sys

import torch
from config import get_config

from models import ModelFactory

logger = logging.getLogger(__name__)


class ModelPreloader:
    """Downloads and caches all models from HuggingFace"""

    def __init__(self):
        self.config = get_config()
        self.device = self._get_device()

    def _get_device(self) -> torch.device:
        """Get available device"""
        if torch.backends.mps.is_available():
            return torch.device("mps")
        elif torch.cuda.is_available():
            return torch.device("cuda")
        else:
            return torch.device("cpu")

    def preload_all(self) -> None:
        """Preload all models from presets.json"""
        models = self.config.get_models()
        total = len(models)

        print(f"\n{'='*60}")
        print(f"Generative Creative Lab - Model Preloader")
        print(f"{'='*60}")
        print(f"Models to download: {total}")
        print(f"Device: {self.device}")
        print(f"Cache location: ~/.cache/huggingface/")
        print(f"{'='*60}\n")

        for i, model_config in enumerate(models, 1):
            model_label = model_config["label"]
            model_slug = model_config["slug"]

            print(f"\n[{i}/{total}] Loading: {model_label}")
            print(f"Slug: {model_slug}")
            print("-" * 60)

            try:
                self.preload_model(model_config)
                print(f"✅ {model_label} loaded successfully!")

            except Exception as e:
                print(f"❌ Error loading {model_label}:")
                print(f"   {e}")
                print(f"   Continuing with next model...")

        print(f"\n{'='*60}")
        print(f"Preloading complete!")
        print(f"{'='*60}\n")

    def preload_model(self, model_config: dict) -> None:
        """
        Preload a single model

        Args:
            model_config: Model configuration from presets.json
        """
        model_slug = model_config["slug"]
        model_path = self.config.get_model_path(model_config)

        logger.debug(f"Preloading model: {model_slug}")
        logger.debug(f"Model path: {model_path}")
        print(f"Path: {model_path}")

        # Create progress callback
        def progress_callback(progress: float, desc: str):
            percentage = int(progress * 100)
            print(f"  [{percentage:3d}%] {desc}")

        # Create model instance
        logger.debug(f"Creating model instance via ModelFactory")
        model = ModelFactory.create_model(model_config, model_path)

        # Load pipeline (downloads if not cached)
        logger.debug(f"Loading pipeline (may download from HuggingFace)")
        status = model.load_pipeline(progress_callback=progress_callback)

        if not model.is_loaded():
            logger.error(f"Failed to load model {model_slug}: {status}")
            raise RuntimeError(f"Failed to load model: {status}")

        # Model is now cached!
        logger.info(f"Model {model_slug} preloaded and cached successfully")
        print(f"  [100%] Cached to HuggingFace cache")

    def preload_by_slug(self, slug: str) -> None:
        """
        Preload a specific model by slug

        Args:
            slug: Model slug (e.g., "zimageturbo", "flux1_dev", "qwen_image")
        """
        model_config = self.config.get_model_by_slug(slug)

        if model_config is None:
            print(f"❌ Error: Model '{slug}' not found in presets.json")
            print(f"\nAvailable models:")
            for model in self.config.get_models():
                print(f"  - {model['slug']}: {model['label']}")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Generative Creative Lab - Model Preloader")
        print(f"{'='*60}")
        print(f"Loading: {model_config['label']}")
        print(f"Device: {self.device}")
        print(f"{'='*60}\n")

        try:
            self.preload_model(model_config)
            print(f"\n✅ {model_config['label']} loaded successfully!")

        except Exception as e:
            print(f"\n❌ Error loading {model_config['label']}:")
            print(f"   {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Preload Generative Creative Lab models from HuggingFace Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python preloader.py                    # Load all models
  python preloader.py --model zimageturbo  # Load Z-Image Turbo only
  python preloader.py --model flux1_dev    # Load Flux.1-dev only
  python preloader.py --model qwen_image   # Load Qwen-Image only

Available model slugs:
  zimageturbo  - Z-Image Turbo (~33GB)
  flux1_dev    - Flux.1 Dev (~24GB)
  qwen_image   - Qwen-Image-2512 (~38GB)
        """,
    )

    parser.add_argument(
        "--model", type=str, help="Model slug to preload (if not specified, loads all models)"
    )

    args = parser.parse_args()

    # Create preloader
    preloader = ModelPreloader()

    # Load specific model or all models
    if args.model:
        preloader.preload_by_slug(args.model)
    else:
        preloader.preload_all()


if __name__ == "__main__":
    main()
