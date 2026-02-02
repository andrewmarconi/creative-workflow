"""
Celery tasks for diffusion image generation and prompt enhancement.

These tasks integrate with the existing lib modules:
- lib/models/base.py, lib/models/flux.py, lib/models/qwen.py, lib/models/zimageturbo.py
- lib/loras/manager.py
- lib/prompt_enhancer.py (HFPromptEnhancer)

Celery is configured with 'solo' pool to avoid fork() issues with MPS on macOS.
This allows tasks to use GPU acceleration (MPS on Apple Silicon, CUDA on NVIDIA).
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from celery import shared_task

# Add lib directory to Python path
lib_path = Path(settings.BASE_DIR) / 'lib'
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from lib.prompt_enhancer import HFPromptEnhancer


@shared_task(bind=True, name='queerchaos.diffusion.tasks.enhance_prompt_task')
def enhance_prompt_task(self, prompt_id):
    """
    Enhance a prompt using HFPromptEnhancer (local LLM).

    Args:
        prompt_id: ID of the Prompt object to enhance

    Returns:
        Dict with enhancement results
    """
    from queerchaos.diffusion.models import Prompt

    prompt = Prompt.objects.get(id=prompt_id)

    # Skip if already enhanced
    if prompt.enhanced_prompt:
        return {
            'status': 'skipped',
            'prompt_id': prompt_id,
            'message': 'Prompt already enhanced'
        }

    # Initialize HF enhancer with local model
    # With Celery 'solo' pool, MPS will be auto-detected and used if available
    enhancer = HFPromptEnhancer(
        model_id="Qwen/Qwen2.5-3B-Instruct",
        style=prompt.enhancement_style,
        creativity=prompt.creativity,
        trigger_words=None,  # No trigger words for base prompt
    )

    # Enhance the prompt
    result = enhancer.enhance_prompt(prompt.source_prompt)

    # Update prompt record
    prompt.enhanced_prompt = result['enhanced_prompt']
    prompt.negative_prompt = result['negative_prompt']
    prompt.enhancement_method = result.get('method', 'huggingface')
    prompt.save()

    return {
        'status': 'success',
        'prompt_id': prompt_id,
        'enhanced': result['enhanced_prompt'][:100] + '...',
        'method': result.get('method', 'huggingface')
    }


@shared_task(bind=True, name='queerchaos.diffusion.tasks.generate_images_task')
def generate_images_task(self, job_id):
    """
    Generate images using diffusion models.

    Args:
        job_id: ID of the DiffusionJob to process

    Returns:
        Dict with job results
    """
    from queerchaos.diffusion.models import DiffusionJob, DiffusionModel, LoraModel

    job = DiffusionJob.objects.get(id=job_id)

    try:
        # Update job status
        job.status = 'processing'
        job.started_at = timezone.now()
        job.save()

        # Get generation parameters
        params = job.get_generation_params()

        # Load the model using the factory pattern from lib
        model = _load_model_instance(job.diffusion_model)

        # Load LoRA if specified
        if job.lora_model:
            # Construct full LoRA path from Django settings
            lora_path_obj = Path(job.lora_model.path)
            if not lora_path_obj.is_absolute():
                # Relative path - combine with base model path from settings
                lora_path = str(settings.MODEL_BASE_PATH / job.lora_model.path)
            else:
                # Already absolute
                lora_path = job.lora_model.path

            # Create LoRA config matching BaseModel.load_lora() expectations
            lora_config = {
                'label': job.lora_model.label,
                'path': job.lora_model.path,
                'prompt': job.lora_model.prompt_suffix,  # Trigger words to append
                'settings': {
                    'strength': params.get('lora_strength', job.lora_model.default_strength)
                }
            }

            # Debug: Log LoRA trigger words
            print(f"DEBUG: Loading LoRA '{job.lora_model.label}'")
            print(f"DEBUG: LoRA trigger words: '{job.lora_model.prompt_suffix}'")

            load_result = model.load_lora(lora_path, lora_config)
            print(f"DEBUG: LoRA load result: {load_result}")

        # Prepare generation parameters (matching BaseModel.generate() signature)
        gen_params = {
            'prompt': params['prompt'],
            'width': params['width'],
            'height': params['height'],
            'steps': params['steps'],  # Not 'num_inference_steps'
            'guidance_scale': params['guidance_scale'],
            'seed': params.get('seed'),
        }

        # Add negative prompt if supported
        if 'negative_prompt' in params:
            gen_params['negative_prompt'] = params['negative_prompt']

        # Generate images (loop for multiple images since generate() returns single image)
        saved_paths = []
        media_dir = Path(settings.MEDIA_ROOT) / 'diffusion' / f'job_{job_id}'
        media_dir.mkdir(parents=True, exist_ok=True)

        num_images = params['num_images']
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for idx in range(num_images):
            # Generate single image
            # Returns: Tuple[Image.Image, Dict] - single image + metadata
            print(f"DEBUG: Generating image {idx+1}/{num_images}")
            print(f"DEBUG: Input prompt: '{gen_params['prompt']}'")

            image, metadata = model.generate(**gen_params)

            print(f"DEBUG: Generated with prompt: '{metadata.get('prompt', 'N/A')}'")
            if job.lora_model:
                print(f"DEBUG: LoRA applied: {metadata.get('lora', 'N/A')}")

            # Use seed from metadata (actual seed used, not requested seed)
            actual_seed = metadata.get('seed', 'unknown')

            # Save image
            filename = f"{job.diffusion_model.slug}_{timestamp}_{actual_seed}_{idx+1:03d}.jpg"
            filepath = media_dir / filename
            image.save(filepath, quality=95)

            # Store relative path from MEDIA_ROOT
            rel_path = str(filepath.relative_to(settings.MEDIA_ROOT))
            saved_paths.append(rel_path)

        # Update job with results
        job.result_images = saved_paths
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()

        # Unload LoRA if it was loaded
        if job.lora_model:
            model.unload_lora()

        return {
            'status': 'success',
            'job_id': job_id,
            'images_count': len(saved_paths),
            'paths': saved_paths
        }

    except Exception as e:
        # Update job with error
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()

        return {
            'status': 'failed',
            'job_id': job_id,
            'error': str(e)
        }


def _load_model_instance(diffusion_model):
    """
    Load a model instance using the lib modules.

    Args:
        diffusion_model: DiffusionModel Django object

    Returns:
        Loaded model instance from lib/models/*
    """
    # Import model classes
    from lib.models import BaseModel, ZImageTurboModel, FluxModel, QwenImageModel

    # Map pipeline names to classes
    model_classes = {
        'ZImagePipeline': ZImageTurboModel,
        'FluxPipeline': FluxModel,
        'QwenImagePipeline': QwenImageModel,
    }

    model_class = model_classes.get(diffusion_model.pipeline)
    if not model_class:
        raise ValueError(f"Unknown pipeline: {diffusion_model.pipeline}")

    # Create model config dict
    model_config = {
        'label': diffusion_model.label,
        'slug': diffusion_model.slug,
        'path': diffusion_model.path,
        'pipeline': diffusion_model.pipeline,
        'settings': diffusion_model.get_settings_dict()
    }

    # Instantiate and load the model
    model_instance = model_class(model_config, diffusion_model.path)
    model_instance.load_pipeline()

    return model_instance
