#!/usr/bin/env python3
"""
QueerChaos 2 - Batch Image Generation with Flux2
Generates images from text prompts using Flux2 diffusion models on Apple Silicon
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import torch
from diffusers import FluxPipeline
from diffusers.schedulers import FlowMatchEulerDiscreteScheduler


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
        print("Phase 1 Complete: Models loaded successfully!")
        print(f"{'='*60}")
        print(f"Device: {device_name}")
        print(f"Prompts to process: {len(config['prompts'])}")
        print(f"Images per prompt: {config['count']}")
        print(f"Total images: {len(config['prompts']) * config['count']}")
        print(f"Output directory: {config['output_dir']}")
        if models['lora_info']:
            print(f"LoRA: {models['lora_info']['name']}")
        print(f"{'='*60}\n")

        print("Phase 2 (Core Generation) not yet implemented.")
        print("Models are loaded and ready for image generation.")

        return 0

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
