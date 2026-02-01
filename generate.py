#!/usr/bin/env python3
"""
QueerChaos 2 - Batch Image Generation with Flux2
Generates images from text prompts using Flux2 diffusion models on Apple Silicon
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch
from PIL import Image
from diffusers import FluxPipeline
from diffusers.schedulers import FlowMatchEulerDiscreteScheduler
from tqdm import tqdm


class Config:
    """Configuration and constants for image generation"""

    # Model IDs
    FLUX2_MODEL_ID = "black-forest-labs/FLUX.1-dev"  # Using Flux 1 Dev as placeholder
    TEXT_ENCODER_ID = "mistralai/Mistral-3-Small"

    # Generation parameters (Flux2 Dev best practices)
    RESOLUTION = 1024
    STEPS = 28  # Default to speed, can be up to 50 for quality
    GUIDANCE_SCALE = 3.5
    JPG_QUALITY = 95

    # Device settings
    DTYPE_FP8 = torch.float8_e4m3fn if hasattr(torch, 'float8_e4m3fn') else torch.float16
    DTYPE_BF16 = torch.bfloat16


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate images using Flux2 diffusion models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use default ./input.json
  %(prog)s my_prompts.json         # Use custom input file
        """
    )

    parser.add_argument(
        'input_file',
        nargs='?',
        default='./input.json',
        help='Path to JSON input file (default: ./input.json)'
    )

    return parser.parse_args()


def validate_json_schema(data: Dict[str, Any]) -> None:
    """
    Validate the input JSON schema

    Args:
        data: Parsed JSON data

    Raises:
        ValueError: If schema validation fails
    """
    # Check required fields
    required_fields = ['count', 'prompts', 'output_dir']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate count
    if not isinstance(data['count'], int) or data['count'] <= 0:
        raise ValueError(f"'count' must be a positive integer, got: {data['count']}")

    # Validate prompts
    if not isinstance(data['prompts'], dict) or len(data['prompts']) == 0:
        raise ValueError("'prompts' must be a non-empty object/dictionary")

    # Validate output_dir
    if not isinstance(data['output_dir'], str):
        raise ValueError(f"'output_dir' must be a string, got: {type(data['output_dir'])}")

    # Validate optional lora field
    if 'lora' in data:
        if not isinstance(data['lora'], dict):
            raise ValueError("'lora' must be an object/dictionary")

        if 'name' not in data['lora'] or 'prompt' not in data['lora']:
            raise ValueError("'lora' object must contain 'name' and 'prompt' fields")

    print("✓ JSON schema validated successfully")


def load_input_json(file_path: str) -> Dict[str, Any]:
    """
    Load and validate input JSON file

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed and validated JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        ValueError: If schema validation fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with open(file_path, 'r') as f:
        data = json.load(f)

    validate_json_schema(data)

    return data


def is_local_lora_path(lora_name: str) -> bool:
    """
    Determine if LoRA name is a local file path or HuggingFace ID

    Args:
        lora_name: LoRA name/path from config

    Returns:
        True if local file path, False if HuggingFace ID
    """
    return lora_name.endswith('.safetensors') or os.path.exists(lora_name)


def setup_device() -> tuple[torch.device, str]:
    """
    Configure device for Apple Silicon optimization

    Returns:
        Tuple of (device, device_name)
    """
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        device_name = "MPS (Apple Silicon)"

        # Set memory fraction for MPS
        torch.mps.set_per_process_memory_fraction(0.9)

        print(f"✓ Using {device_name}")
        return device, device_name
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        device_name = "CUDA"
        print(f"✓ Using {device_name}")
        return device, device_name
    else:
        device = torch.device("cpu")
        device_name = "CPU"
        print(f"⚠ Using {device_name} (slower, MPS not available)")
        return device, device_name


def load_models(config: Dict[str, Any], device: torch.device) -> Dict[str, Any]:
    """
    Load Flux2 pipeline, text encoder, and optional LoRA

    Args:
        config: Input configuration dictionary
        device: Torch device to load models on

    Returns:
        Dictionary containing loaded models and pipeline
    """
    print("\nLoading models...")

    # Load Flux2 pipeline with fp8 optimization
    print(f"Loading Flux2 Dev pipeline...")

    try:
        # Note: Using Flux 1 Dev as Flux 2 may not be publicly available yet
        # Adjust model ID when Flux2 Dev is released
        pipeline = FluxPipeline.from_pretrained(
            Config.FLUX2_MODEL_ID,
            torch_dtype=Config.DTYPE_BF16,  # Using bf16 for now, fp8 may need additional setup
            low_cpu_mem_usage=True,
        )

        # Configure scheduler (FlowMatchEulerDiscreteScheduler is default for Flux)
        pipeline.scheduler = FlowMatchEulerDiscreteScheduler.from_config(
            pipeline.scheduler.config
        )

        # Move to device
        pipeline = pipeline.to(device)

        print(f"✓ Flux2 Dev (bf16) loaded")  # Note: fp8 requires additional quantization

    except Exception as e:
        print(f"✗ Failed to load Flux2 pipeline: {e}")
        raise

    # Load LoRA if specified
    lora_info = None
    if 'lora' in config:
        lora_config = config['lora']
        lora_name = lora_config['name']

        try:
            if is_local_lora_path(lora_name):
                # Load from local file
                if not os.path.exists(lora_name):
                    raise FileNotFoundError(f"LoRA file not found: {lora_name}")

                print(f"Loading LoRA from local file: {lora_name}")
                pipeline.load_lora_weights(lora_name)
                print(f"✓ LoRA loaded from: {lora_name}")
            else:
                # Load from HuggingFace Hub
                print(f"Loading LoRA from HuggingFace: {lora_name}")
                pipeline.load_lora_weights(lora_name)
                print(f"✓ LoRA loaded: {lora_name}")

            lora_info = lora_config

        except Exception as e:
            print(f"✗ Failed to load LoRA '{lora_name}': {e}")
            raise

    # Enable memory optimizations
    if device.type == "mps":
        # MPS-specific optimizations
        pipeline.enable_attention_slicing()
    elif device.type == "cuda":
        # CUDA-specific optimizations
        pipeline.enable_model_cpu_offload()
        pipeline.enable_attention_slicing()

    return {
        'pipeline': pipeline,
        'lora_info': lora_info,
        'device': device
    }


def generate_image(
    pipeline: FluxPipeline,
    prompt: str,
    seed: int,
    device: torch.device
) -> Image.Image:
    """
    Generate a single image from a prompt

    Args:
        pipeline: Loaded Flux pipeline
        prompt: Text prompt for generation
        seed: Random seed for reproducibility
        device: Torch device

    Returns:
        Generated PIL Image
    """
    # Set random seed for reproducibility
    generator = torch.Generator(device=device.type if device.type != "mps" else "cpu")
    generator.manual_seed(seed)

    # Generate image with best practice parameters
    image = pipeline(
        prompt=prompt,
        num_inference_steps=Config.STEPS,
        guidance_scale=Config.GUIDANCE_SCALE,
        height=Config.RESOLUTION,
        width=Config.RESOLUTION,
        generator=generator,
    ).images[0]

    return image


def save_image_as_jpg(image: Image.Image, output_path: Path) -> None:
    """
    Save image as high-quality JPG

    Args:
        image: PIL Image to save
        output_path: Path where to save the image
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as JPG with high quality
    image.save(output_path, "JPEG", quality=Config.JPG_QUALITY, optimize=True)


def get_output_filename(prefix: str, index: int, total_count: int) -> str:
    """
    Generate output filename with correct padding

    Args:
        prefix: File prefix from prompt key
        index: Current image index (1-based)
        total_count: Total number of images to generate

    Returns:
        Formatted filename
    """
    # Determine padding based on total count
    if total_count > 99:
        padding = 3
    else:
        padding = 3  # Always use 3-digit padding as per PRD

    return f"{prefix}_{index:0{padding}d}.jpg"


def load_checkpoint(output_dir: Path) -> set:
    """
    Load checkpoint file if it exists

    Args:
        output_dir: Output directory path

    Returns:
        Set of completed image filenames
    """
    checkpoint_path = output_dir / ".checkpoint.json"

    if not checkpoint_path.exists():
        return set()

    try:
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        completed = set(checkpoint_data.get('completed_images', []))
        print(f"✓ Loaded checkpoint: {len(completed)} images already completed")
        return completed
    except Exception as e:
        print(f"⚠ Warning: Failed to load checkpoint: {e}")
        return set()


def save_checkpoint(output_dir: Path, completed_images: List[str], total_expected: int) -> None:
    """
    Save checkpoint file with current progress

    Args:
        output_dir: Output directory path
        completed_images: List of completed image filenames
        total_expected: Total number of images expected
    """
    checkpoint_path = output_dir / ".checkpoint.json"

    checkpoint_data = {
        "completed_images": completed_images,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_expected": total_expected
    }

    try:
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    except Exception as e:
        print(f"⚠ Warning: Failed to save checkpoint: {e}")


def save_metadata(
    config: Dict[str, Any],
    generation_metadata: List[Dict[str, Any]],
    output_dir: Path
) -> None:
    """
    Save generation metadata to JSON file

    Args:
        config: Input configuration
        generation_metadata: List of metadata for each generated image
        output_dir: Output directory path
    """
    metadata = {
        "batch_config": {
            "count": config['count'],
        },
        "model_config": {
            "diffusion_model": Config.FLUX2_MODEL_ID,
            "steps": Config.STEPS,
            "guidance_scale": Config.GUIDANCE_SCALE,
            "scheduler": "FlowMatchEulerDiscreteScheduler"
        },
        "images": generation_metadata
    }

    # Add LoRA info if present
    if 'lora' in config:
        metadata['batch_config']['lora'] = config['lora']

    # Save to file
    metadata_path = output_dir / "generation_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to {metadata_path}")


def process_prompts(
    config: Dict[str, Any],
    models: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Process all prompts and generate images

    Args:
        config: Input configuration
        models: Loaded models dictionary

    Returns:
        List of generation metadata for each image
    """
    pipeline = models['pipeline']
    lora_info = models['lora_info']
    device = models['device']
    output_dir = Path(config['output_dir'])

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate total images
    total_images = len(config['prompts']) * config['count']
    generation_metadata = []

    # Load checkpoint to resume from previous run
    completed_images_set = load_checkpoint(output_dir)
    completed_images_list = list(completed_images_set)

    # Create progress bar
    pbar = tqdm(
        total=total_images,
        desc="Processing",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {postfix}]"
    )

    success_count = 0
    failed_count = 0
    skipped_count = len(completed_images_set)

    # Process each prompt
    for prompt_prefix, prompt_text in config['prompts'].items():
        # Append LoRA prompt if specified
        if lora_info:
            full_prompt = f"{prompt_text}, {lora_info['prompt']}"
        else:
            full_prompt = prompt_text

        # Generate multiple images for this prompt
        for i in range(1, config['count'] + 1):
            # Generate random seed
            seed = random.randint(0, 2**32 - 1)

            # Create output filename
            filename = get_output_filename(prompt_prefix, i, config['count'])
            output_path = output_dir / filename

            # Update progress bar description
            pbar.set_description(f"Processing {prompt_prefix}")

            # Check if image already exists in checkpoint
            if filename in completed_images_set:
                # Skip this image - already generated
                metadata = {
                    "filename": filename,
                    "prompt": full_prompt,
                    "seed": seed,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "skipped"
                }
                generation_metadata.append(metadata)

                # Update progress bar
                pbar.set_postfix({
                    "Success": success_count,
                    "Failed": failed_count,
                    "Skipped": skipped_count
                })
                pbar.update(1)
                continue

            try:
                # Generate image
                image = generate_image(pipeline, full_prompt, seed, device)

                # Save as JPG
                save_image_as_jpg(image, output_path)

                # Record metadata
                metadata = {
                    "filename": filename,
                    "prompt": full_prompt,
                    "seed": seed,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "success"
                }
                generation_metadata.append(metadata)
                success_count += 1

                # Update checkpoint with completed image
                completed_images_list.append(filename)
                save_checkpoint(output_dir, completed_images_list, total_images)

                # Clear MPS cache if using Apple Silicon
                if device.type == "mps":
                    torch.mps.empty_cache()

            except Exception as e:
                # Record error in metadata
                metadata = {
                    "filename": filename,
                    "prompt": full_prompt,
                    "seed": seed,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "failed",
                    "error": str(e)
                }
                generation_metadata.append(metadata)
                failed_count += 1

                # Log error but continue
                tqdm.write(f"✗ Error generating {filename}: {e}")

            # Update progress bar
            pbar.set_postfix({
                "Success": success_count,
                "Failed": failed_count,
                "Skipped": skipped_count
            })
            pbar.update(1)

    pbar.close()

    return generation_metadata


def main():
    """Main entry point"""

    # Parse arguments
    args = parse_arguments()

    try:
        # Load and validate input JSON
        print(f"Loading input from: {args.input_file}")
        config = load_input_json(args.input_file)

        # Setup device (Apple Silicon optimization)
        device, device_name = setup_device()

        # Load models
        models = load_models(config, device)

        print(f"\n{'='*60}")
        print("Models loaded successfully!")
        print(f"{'='*60}")
        print(f"Device: {device_name}")
        print(f"Prompts to process: {len(config['prompts'])}")
        print(f"Images per prompt: {config['count']}")
        print(f"Total images: {len(config['prompts']) * config['count']}")
        print(f"Output directory: {config['output_dir']}")
        if models['lora_info']:
            print(f"LoRA: {models['lora_info']['name']}")
        print(f"{'='*60}\n")

        # Process prompts and generate images
        generation_metadata = process_prompts(config, models)

        # Save metadata
        output_dir = Path(config['output_dir'])
        save_metadata(config, generation_metadata, output_dir)

        # Summary
        success_count = sum(1 for m in generation_metadata if m['status'] == 'success')
        failed_count = sum(1 for m in generation_metadata if m['status'] == 'failed')

        print(f"\n{'='*60}")
        print("Generation Complete!")
        print(f"{'='*60}")
        print(f"Total images: {len(generation_metadata)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Output directory: {config['output_dir']}")
        print(f"{'='*60}\n")

        # Return appropriate exit code
        if failed_count > 0 and success_count > 0:
            return 2  # Partial success
        elif failed_count > 0 and success_count == 0:
            return 1  # All failed
        else:
            return 0  # All succeeded

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ JSON Parse Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"✗ Validation Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Fatal Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
