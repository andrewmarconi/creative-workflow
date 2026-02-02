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

# Module-level enhancer cache: keeps the LLM warm between task invocations.
_enhancer_cache = {}  # {model_id: HFPromptEnhancer}


def _get_enhancer(model_id="Qwen/Qwen2.5-3B-Instruct"):
    """Return a cached HFPromptEnhancer instance, loading on first call."""
    if model_id not in _enhancer_cache:
        print(f"DEBUG: Loading enhancer '{model_id}' (cold start)")
        _enhancer_cache[model_id] = HFPromptEnhancer(model_id=model_id)
    else:
        print(f"DEBUG: Using warm enhancer '{model_id}'")
    return _enhancer_cache[model_id]


@shared_task(bind=True, name='cw.diffusion.tasks.enhance_prompt_task')
def enhance_prompt_task(self, prompt_id):
    """
    Enhance a prompt using HFPromptEnhancer (local LLM).

    Args:
        prompt_id: ID of the Prompt object to enhance

    Returns:
        Dict with enhancement results
    """
    from cw.diffusion.models import Prompt

    prompt = Prompt.objects.get(id=prompt_id)

    # Skip if already enhanced
    if prompt.enhanced_prompt:
        return {
            'status': 'skipped',
            'prompt_id': prompt_id,
            'message': 'Prompt already enhanced'
        }

    # Get cached enhancer and configure for this prompt
    enhancer = _get_enhancer()
    enhancer.style = prompt.enhancement_style
    enhancer.creativity = prompt.creativity
    enhancer.trigger_words = None

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


def _evict_enhancer():
    """Free VRAM occupied by the prompt enhancer LLM."""
    import torch
    for key in list(_enhancer_cache.keys()):
        print(f"DEBUG: Evicting enhancer '{key}' to free VRAM")
        del _enhancer_cache[key]
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif hasattr(torch, 'mps') and hasattr(torch.mps, 'empty_cache'):
        torch.mps.empty_cache()


@shared_task(bind=True, name='cw.diffusion.tasks.generate_images_task')
def generate_images_task(self, job_id):
    """
    Generate images using diffusion models.

    Args:
        job_id: ID of the DiffusionJob to process

    Returns:
        Dict with job results
    """
    from cw.diffusion.models import DiffusionJob, DiffusionModel, LoraModel

    job_id = int(job_id)
    job = DiffusionJob.objects.get(id=job_id)

    try:
        # Update job status
        job.status = 'processing'
        job.started_at = timezone.now()
        job.save()

        # Get generation parameters
        params = job.get_generation_params()

        # Evict the prompt enhancer LLM from VRAM before loading diffusion model
        _evict_enhancer()

        # Load the model using the factory pattern from lib
        model = _load_model_instance(job.diffusion_model)

        # Load LoRA if specified
        if job.lora_model:
            # Resolve LoRA file path
            if job.lora_model.path:
                lora_path_obj = Path(job.lora_model.path)
                if not lora_path_obj.is_absolute():
                    lora_path = str(settings.MODEL_BASE_PATH / job.lora_model.path)
                else:
                    lora_path = job.lora_model.path
            elif job.lora_model.air:
                # No path set — derive filename from AIR URN
                from lib.civitai import parse_air
                _, version_id = parse_air(job.lora_model.air)
                lora_path = str(settings.MODEL_BASE_PATH / 'loras' / f'civitai_{version_id}.safetensors')
            else:
                raise RuntimeError(f"LoRA '{job.lora_model.label}' has no path and no AIR")

            # Create LoRA config matching BaseModel.load_lora() expectations
            lora_config = {
                'label': job.lora_model.label,
                'path': job.lora_model.path,
                'prompt': job.lora_model.prompt_suffix,
                'negative_prompt': job.lora_model.negative_prompt_suffix,
                'settings': {
                    'strength': params.get('lora_strength', job.lora_model.default_strength)
                }
            }

            # Auto-download from CivitAI if file missing and AIR is set
            if not Path(lora_path).exists() and job.lora_model.air:
                from lib.civitai import download_lora
                lora_path = download_lora(
                    job.lora_model.air, lora_path, settings.CIVITAI_API_KEY
                )

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

        # Add negative prompt if supported, appending LoRA negative suffix
        if 'negative_prompt' in params:
            neg = params['negative_prompt'] or ''
            if job.lora_model:
                lora_neg = job.lora_model.negative_prompt_suffix
                if lora_neg:
                    neg = f"{neg}, {lora_neg}" if neg.strip() else lora_neg
            gen_params['negative_prompt'] = neg

        # Debug: Log final generation parameters
        print(f"DEBUG: Final prompt: '{gen_params['prompt']}'")
        if 'negative_prompt' in gen_params:
            print(f"DEBUG: Final negative prompt: '{gen_params['negative_prompt']}'")
        print(f"DEBUG: {gen_params['width']}x{gen_params['height']}, steps={gen_params['steps']}, cfg={gen_params['guidance_scale']}, seed={gen_params.get('seed')}")

        # Generate images (loop for multiple images since generate() returns single image)
        saved_paths = []
        media_dir = Path(settings.MEDIA_ROOT) / 'diffusion'
        media_dir.mkdir(parents=True, exist_ok=True)

        num_images = params['num_images']
        prompt_id = job.prompt_id
        model_id = job.diffusion_model_id
        lora_id = job.lora_model_id or 0

        import random
        for idx in range(num_images):
            # Randomize seed for each image unless explicitly set
            if params.get('seed') is None:
                gen_params['seed'] = random.randint(0, 2**32 - 1)
            print(f"DEBUG: Generating image {idx+1}/{num_images}, seed={gen_params['seed']}")
            image, metadata = model.generate(**gen_params)

            # Filename: {jobID}.{imageNo}-{promptID}-{modelID}-{loraID}.jpg
            img_no = idx + 1 if num_images > 1 else 0
            filename = f"{job_id:05d}.{img_no:02d}-{prompt_id:03d}-{model_id:03d}-{lora_id:03d}.jpg"
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


# Module-level model cache: keeps the loaded model warm between task invocations.
# Safe because Celery is configured with 'solo' pool (single-threaded worker).
_model_cache = {}  # {slug: model_instance}


def _load_model_instance(diffusion_model):
    """
    Load a model instance using the lib modules, with warm caching.

    If the requested model is already loaded, returns the cached instance.
    If a different model is cached, it is unloaded first (one model at a time).

    Args:
        diffusion_model: DiffusionModel Django object

    Returns:
        Loaded model instance from lib/models/*
    """
    slug = diffusion_model.slug

    # Return cached model if it matches and pipeline is loaded
    if slug in _model_cache:
        cached = _model_cache[slug]
        if cached.pipeline is not None:
            print(f"DEBUG: Using warm model '{slug}'")
            return cached
        else:
            print(f"DEBUG: Cached model '{slug}' has no pipeline, reloading")
            del _model_cache[slug]

    # Evict any previously cached model (one model at a time for memory)
    for old_slug, old_model in list(_model_cache.items()):
        print(f"DEBUG: Evicting model '{old_slug}' to load '{slug}'")
        try:
            if hasattr(old_model, 'pipeline') and old_model.pipeline is not None:
                del old_model.pipeline
            import torch
            if hasattr(torch, 'mps') and hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        del _model_cache[old_slug]

    from lib.models import ModelFactory

    # Create model config dict
    model_config = {
        'label': diffusion_model.label,
        'slug': diffusion_model.slug,
        'path': diffusion_model.path,
        'pipeline': diffusion_model.pipeline,
        'settings': diffusion_model.get_settings_dict()
    }

    # Instantiate and load the model
    print(f"DEBUG: Loading model '{slug}' (cold start)")
    model_instance = ModelFactory.create_model(model_config, diffusion_model.path)
    result = model_instance.load_pipeline()

    # Only cache if pipeline actually loaded
    if model_instance.pipeline is None:
        raise RuntimeError(f"Failed to load model '{slug}': {result}")

    _model_cache[slug] = model_instance
    return model_instance
