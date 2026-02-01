#!/usr/bin/env python3
"""
QueerChaos 2 - Gradio Web Interface
Multi-model support with dynamic LoRA filtering
Supports: Z-Image Turbo, Flux.1-dev, Qwen-Image-2512
"""

import os
import random
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import torch
from PIL import Image
import gradio as gr

from config import get_config
from loras import LoRAManager
from models import ModelFactory, BaseModel

# Suppress expected warnings on Apple Silicon
warnings.filterwarnings('ignore', message='.*CUDA is not available.*')
warnings.filterwarnings('ignore', message='.*torch_xla.*')


class ImageGenerator:
    """Manages model loading and image generation with multi-model support"""

    def __init__(self):
        self.config = get_config()
        self.lora_manager = LoRAManager()
        self.current_model: Optional[BaseModel] = None
        self.current_model_slug: Optional[str] = None

    def load_model(self, model_label: str, progress=gr.Progress()) -> Tuple[str, gr.update, gr.update, gr.update, gr.update, gr.update]:
        """
        Load selected model

        Args:
            model_label: Model label from dropdown

        Returns:
            Tuple of (status message, lora_update, steps_update, guidance_update, negative_prompt_update, resolution_update)
        """
        try:
            # Get model config
            model_config = self.config.get_model_by_label(model_label)
            if model_config is None:
                return (f"Error: Model '{model_label}' not found",
                        gr.update(), gr.update(), gr.update(), gr.update(), gr.update())

            model_slug = model_config["slug"]

            # If same model already loaded, skip
            if self.current_model is not None and self.current_model_slug == model_slug:
                # Just update UI components
                return self._update_ui_for_model(model_config, f"{model_label} already loaded")

            # Get model path
            model_path = self.config.get_model_path(model_config)

            # Create model instance
            progress(0.1, desc=f"Initializing {model_label}...")
            self.current_model = ModelFactory.create_model(model_config, model_path)
            self.current_model_slug = model_slug

            # Load pipeline
            progress(0.3, desc=f"Loading {model_label} pipeline...")
            status = self.current_model.load_pipeline(progress_callback=progress)

            # Update UI components
            return self._update_ui_for_model(model_config, status)

        except Exception as e:
            return (f"Error loading model: {e}",
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())

    def _update_ui_for_model(self, model_config: Dict, status_message: str) -> Tuple[str, gr.update, gr.update, gr.update, gr.update, gr.update]:
        """Update UI components based on loaded model settings"""
        model_slug = model_config["slug"]
        settings = model_config.get("settings", {})

        # Get compatible LoRAs
        lora_choices = self.lora_manager.get_lora_choices(model_slug)

        # Update UI components
        lora_update = gr.update(choices=lora_choices, value="None (No LoRA)")
        steps_update = gr.update(value=settings.get("steps", 20))
        guidance_update = gr.update(value=settings.get("guidance_scale", 7.5))

        # Show/hide negative prompt based on support
        supports_negative = settings.get("supports_negative_prompt", False)
        negative_prompt_update = gr.update(visible=supports_negative)

        # Update resolution
        resolution_update = gr.update(value=settings.get("resolution", 1024))

        return (status_message, lora_update, steps_update, guidance_update,
                negative_prompt_update, resolution_update)

    def load_lora(self, lora_label: str) -> str:
        """Load selected LoRA"""
        if self.current_model is None:
            return "Error: No model loaded"

        # Handle "None" selection
        if lora_label == "None (No LoRA)":
            return self.current_model.unload_lora()

        # Get LoRA config
        lora_config = self.lora_manager.get_lora_by_label(lora_label, self.current_model_slug)
        if lora_config is None:
            return f"Error: LoRA '{lora_label}' not found"

        # Get LoRA path
        lora_path = self.lora_manager.get_lora_path(lora_config)

        # Load LoRA
        return self.current_model.load_lora(lora_path, lora_config)

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        steps: int,
        guidance_scale: float,
        resolution: int,
        seed: int,
        count: int,
        output_dir: str,
        progress=gr.Progress()
    ) -> Tuple[List[Image.Image], str, str]:
        """
        Generate images based on parameters

        Returns:
            Tuple of (list of generated images, status message, metadata)
        """
        if self.current_model is None:
            return [], "Error: No model loaded. Please select a model.", ""

        if not prompt.strip():
            return [], "Error: Prompt cannot be empty", ""

        # Setup output directory
        full_output_dir = self.config.base_output_path / output_dir
        full_output_dir.mkdir(parents=True, exist_ok=True)

        generated_images = []
        errors = []
        all_metadata = []

        # Generate images
        for i in range(count):
            try:
                progress((i / count), desc=f"Generating image {i+1}/{count}...")

                # Calculate seed for this image
                current_seed = seed + i

                # Generate single image
                image, metadata = self.current_model.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt if (negative_prompt and negative_prompt.strip()) else None,
                    steps=steps,
                    guidance_scale=guidance_scale,
                    width=resolution,
                    height=resolution,
                    seed=current_seed,
                    progress_callback=lambda p, desc: progress(
                        (i + p) / count, desc=f"Image {i+1}/{count}: {desc}"
                    ),
                )

                # Save image
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                model_slug = self.current_model_slug or "unknown"
                filename = f"{model_slug}_{timestamp}_{current_seed}_{i+1:03d}.jpg"
                output_path = full_output_dir / filename
                image.save(output_path, "JPEG", quality=95, optimize=True)

                generated_images.append(image)
                all_metadata.append(metadata)

            except Exception as e:
                errors.append(f"Image {i+1}: {str(e)}")
                continue

        progress(1.0, desc="Generation complete!")

        # Build status message
        if len(generated_images) == count:
            status = f"Successfully generated {count} image(s) in {full_output_dir}"
        elif len(generated_images) > 0:
            status = f"Generated {len(generated_images)}/{count} images. Errors: {'; '.join(errors)}"
        else:
            status = f"Failed to generate images. Errors: {'; '.join(errors)}"

        # Format metadata for display
        metadata_display = ""
        if all_metadata:
            first_meta = all_metadata[0]
            metadata_display = f"Model: {first_meta.get('model', 'Unknown')}\n"
            metadata_display += f"Prompt: {first_meta.get('prompt', '')}\n"
            if first_meta.get('negative_prompt'):
                metadata_display += f"Negative: {first_meta.get('negative_prompt', '')}\n"
            metadata_display += f"Steps: {first_meta.get('steps')}, Guidance: {first_meta.get('guidance_scale')}\n"
            metadata_display += f"Resolution: {first_meta.get('width')}x{first_meta.get('height')}\n"
            if first_meta.get('lora'):
                metadata_display += f"LoRA: {first_meta.get('lora')}\n"

        return generated_images, status, metadata_display


# Global generator instance
generator = ImageGenerator()


def randomize_seed() -> int:
    """Generate a random seed"""
    return random.randint(0, 2**32 - 1)


def build_interface():
    """Build Gradio interface"""

    config = get_config()

    with gr.Blocks(title="QueerChaos 2 - Multi-Model Generator") as interface:
        gr.Markdown("# QueerChaos 2 - Multi-Model Image Generator")
        gr.Markdown("Generate images using Z-Image Turbo, Flux.1-dev, or Qwen-Image with optional LoRAs")

        with gr.Row():
            with gr.Column(scale=1):
                # Model selection
                model_selector = gr.Dropdown(
                    label="Model",
                    choices=config.get_model_choices(),
                    value=config.get_model_choices()[0],
                    interactive=True
                )

                load_model_button = gr.Button("Load Model", variant="secondary")

                # Input controls
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Enter your prompt here...",
                    lines=3
                )

                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    placeholder="Enter negative prompt (if supported)...",
                    lines=2,
                    visible=False  # Hidden by default, shown for compatible models
                )

                lora_selector = gr.Dropdown(
                    label="LoRA",
                    choices=["None (No LoRA)"],
                    value="None (No LoRA)",
                    interactive=True
                )

                with gr.Row():
                    steps = gr.Slider(
                        minimum=4,
                        maximum=100,
                        value=20,
                        step=1,
                        label="Steps"
                    )

                    guidance_scale = gr.Slider(
                        minimum=0.0,
                        maximum=15.0,
                        value=7.5,
                        step=0.1,
                        label="Guidance Scale"
                    )

                resolution = gr.Slider(
                    minimum=512,
                    maximum=2048,
                    value=1024,
                    step=64,
                    label="Resolution (square)"
                )

                with gr.Row():
                    seed = gr.Number(
                        label="Seed",
                        value=randomize_seed(),
                        precision=0
                    )
                    seed_button = gr.Button("🎲", size="sm")

                count = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=1,
                    step=1,
                    label="Count"
                )

                output_dir = gr.Textbox(
                    label="Output Directory (inside outputs/)",
                    value="./genocide",
                    placeholder="e.g., ./genocide"
                )

                generate_button = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                # Output
                status_output = gr.Textbox(
                    label="Status",
                    value="Select and load a model to begin",
                    interactive=False,
                    lines=3
                )

                metadata_output = gr.Textbox(
                    label="Generation Metadata",
                    interactive=False,
                    lines=6,
                    placeholder="Metadata will appear here after generation..."
                )

                image_output = gr.Gallery(
                    label="Generated Images",
                    show_label=True,
                    columns=2,
                    height="auto"
                )

        # Event handlers
        seed_button.click(
            fn=randomize_seed,
            outputs=seed
        )

        load_model_button.click(
            fn=generator.load_model,
            inputs=[model_selector],
            outputs=[status_output, lora_selector, steps, guidance_scale,
                     negative_prompt, resolution]
        )

        # Update LoRAs when model changes
        model_selector.change(
            fn=lambda: "Model changed. Click 'Load Model' to load the new model.",
            outputs=status_output
        )

        # Load LoRA when selection changes
        lora_selector.change(
            fn=generator.load_lora,
            inputs=[lora_selector],
            outputs=status_output
        )

        generate_button.click(
            fn=generator.generate,
            inputs=[prompt, negative_prompt, steps, guidance_scale, resolution,
                    seed, count, output_dir],
            outputs=[image_output, status_output, metadata_output]
        )

        # Load default model on startup
        interface.load(
            fn=generator.load_model,
            inputs=[model_selector],
            outputs=[status_output, lora_selector, steps, guidance_scale,
                     negative_prompt, resolution]
        )

    return interface


def main():
    """Main entry point"""

    # Set environment variables for better MPS memory management
    os.environ.setdefault('PYTORCH_MPS_HIGH_WATERMARK_RATIO', '0.0')

    # Build and launch interface
    interface = build_interface()
    interface.queue()  # Enable queuing for progress tracking
    interface.launch(
        share=False,  # Set to True to create a public link
        server_name="0.0.0.0",  # Allow external access
        server_port=7860  # Default Gradio port
    )


if __name__ == "__main__":
    main()
