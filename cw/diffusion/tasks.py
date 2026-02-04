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
import logging
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger(__name__)

# Add lib directory to Python path
lib_path = Path(settings.BASE_DIR) / 'lib'
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from lib.prompt_enhancer import HFPromptEnhancer
from lib.civitai import download_lora, parse_air

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


@shared_task(bind=True, name='cw.diffusion.tasks.download_lora_task')
def download_lora_task(self, lora_id):
    """
    Download a LoRA from CivitAI in the background.

    Args:
        lora_id: ID of the LoraModel to download

    Returns:
        Dict with download results
    """
    from cw.diffusion.models import LoraModel

    lora = LoraModel.objects.get(id=lora_id)

    if not lora.air:
        return {
            'status': 'failed',
            'lora_id': lora_id,
            'error': 'No AIR URN configured for this LoRA'
        }

    try:
        # Derive filename from AIR URN
        _, version_id = parse_air(lora.air)
        dest_path = str(settings.MODEL_BASE_PATH / 'loras' / f'civitai_{version_id}.safetensors')

        # Check if already downloaded
        if Path(dest_path).exists():
            logger.info(f"LoRA '{lora.label}' already exists at {dest_path}")
            return {
                'status': 'skipped',
                'lora_id': lora_id,
                'message': 'LoRA file already exists',
                'path': dest_path
            }

        # Download the file
        logger.info(f"Downloading LoRA '{lora.label}' from CivitAI (version {version_id})")
        downloaded_path = download_lora(lora.air, dest_path, settings.CIVITAI_API_KEY)

        logger.info(f"Successfully downloaded LoRA '{lora.label}' to {downloaded_path}")
        return {
            'status': 'success',
            'lora_id': lora_id,
            'path': downloaded_path
        }

    except Exception as e:
        logger.error(f"Failed to download LoRA '{lora.label}': {e}")
        return {
            'status': 'failed',
            'lora_id': lora_id,
            'error': str(e)
        }


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

        # CRITICAL: Always unload any existing LoRA first to ensure clean state
        # This prevents LoRA state from persisting between jobs
        if model.current_lora is not None:
            logger.info(f"Unloading previous LoRA '{model.current_lora['label']}' to ensure clean state")
            model.unload_lora()

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

            # Add clip_skip if set on LoRA
            if job.lora_model.clip_skip is not None:
                lora_config['settings']['clip_skip'] = job.lora_model.clip_skip

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
        # BaseModel.generate() handles all LoRA overrides internally via _resolve_guidance_scale()
        # and _build_prompts() (appends LoRA trigger words and negative prompts)
        gen_params = {
            'prompt': params['prompt'],
            'negative_prompt': params.get('negative_prompt'),
            'width': params['width'],
            'height': params['height'],
            'steps': params['steps'],
            'guidance_scale': params['guidance_scale'],
            'seed': params.get('seed'),
            'scheduler': params.get('scheduler'),  # Job/model scheduler override
        }

        # Debug: Log generation parameters being passed to model
        # Note: BaseModel may modify these (LoRA triggers, guidance_scale resolution, etc.)
        print(f"DEBUG: Input prompt: '{gen_params['prompt']}'")
        if gen_params.get('negative_prompt'):
            print(f"DEBUG: Input negative prompt: '{gen_params['negative_prompt']}'")
        print(f"DEBUG: Input params: {gen_params['width']}x{gen_params['height']}, steps={gen_params['steps']}, cfg={gen_params['guidance_scale']}, seed={gen_params.get('seed')}, scheduler={gen_params.get('scheduler')}")

        # Generate images (loop for multiple images since generate() returns single image)
        saved_paths = []
        images_metadata = []  # Collect metadata for each image
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

            logger.info(f"Generating image {idx+1}/{num_images} (seed: {gen_params['seed']}, steps: {gen_params['steps']})")

            # Progress callback for generation (defensive implementation)
            # Try to handle multiple possible signatures
            total_steps = gen_params['steps']
            callback_called = [False]  # Track if callback is ever called

            def gen_progress(*args, **kwargs):
                # Log first call to see actual signature
                if not callback_called[0]:
                    logger.info(f"  Callback CALLED! args={len(args)}, kwargs={list(kwargs.keys())}")
                    callback_called[0] = True

                # Try to extract step number from various possible signatures
                step = None
                if len(args) >= 2:
                    # Could be (step, timestep, ...) or (pipe, step, timestep, ...)
                    step = args[0] if isinstance(args[0], int) else args[1] if len(args) > 1 and isinstance(args[1], int) else None

                if step is not None and (step == 0 or step % 5 == 0 or step == total_steps - 1):
                    logger.info(f"  Step {step+1}/{total_steps}")

                # Return callback_kwargs if it's the last argument
                if args and isinstance(args[-1], dict):
                    return args[-1]
                return kwargs if kwargs else None

            gen_params['progress_callback'] = gen_progress
            image, metadata = model.generate(**gen_params)
            logger.info(f"Image {idx+1}/{num_images} generated successfully")

            # Filename format:
            # - With identifier: {identifier}-{jobID}.{imageNo}.jpg
            # - Without identifier: {jobID}.{imageNo}-p{promptID}-m{modelID}-l{loraID}.jpg
            img_no = idx + 1 if num_images > 1 else 0
            if job.identifier:
                # Sanitize identifier for filename (replace spaces, remove special chars)
                safe_id = "".join(c if c.isalnum() or c in '-_' else '-' for c in job.identifier)
                filename = f"{safe_id}-{job_id:05d}.{img_no:02d}.jpg"
            else:
                filename = f"{job_id:05d}.{img_no:02d}-p{prompt_id:03d}-m{model_id:03d}-l{lora_id:03d}.jpg"
            filepath = media_dir / filename
            image.save(filepath, quality=95)

            # Store relative path from MEDIA_ROOT
            rel_path = str(filepath.relative_to(settings.MEDIA_ROOT))
            saved_paths.append(rel_path)

            # Collect metadata for this image
            images_metadata.append({
                'image_index': idx,
                'filename': filename,
                'seed': gen_params.get('seed'),
                'pipeline_metadata': metadata
            })

        # Build comprehensive generation metadata using actual values from pipeline
        # Use first image's pipeline metadata for common parameters (all images use same settings except seed)
        first_pipeline_meta = images_metadata[0]['pipeline_metadata'] if images_metadata else {}

        generation_metadata = {
            'identifier': job.identifier or None,
            'model': {
                'slug': job.diffusion_model.slug,
                'label': job.diffusion_model.label,
                'path': job.diffusion_model.path,
                'pipeline': job.diffusion_model.pipeline,
                'base_architecture': job.diffusion_model.base_architecture,
            },
            'lora': {
                'label': job.lora_model.label,
                'path': job.lora_model.path,
                'air': job.lora_model.air,
                'strength': params.get('lora_strength', job.lora_model.default_strength),
                'guidance_scale': job.lora_model.guidance_scale,
                'clip_skip': job.lora_model.clip_skip,
            } if job.lora_model else None,
            'prompt': {
                'source': job.prompt.source_prompt,
                'enhanced': job.prompt.enhanced_prompt,
                'final': first_pipeline_meta.get('prompt', gen_params['prompt']),  # Use actual prompt with LoRA triggers
                'negative': first_pipeline_meta.get('negative_prompt', gen_params.get('negative_prompt')),
            },
            'parameters': {
                'width': first_pipeline_meta.get('width', gen_params['width']),
                'height': first_pipeline_meta.get('height', gen_params['height']),
                'steps': first_pipeline_meta.get('steps', gen_params['steps']),
                'guidance_scale': first_pipeline_meta.get('guidance_scale', gen_params['guidance_scale']),  # Use ACTUAL guidance_scale
                'scheduler': first_pipeline_meta.get('scheduler'),  # Actual scheduler used
                'num_images': num_images,
            },
            'images': images_metadata,
            'generated_at': timezone.now().isoformat(),
        }

        # Update job with results
        job.result_images = saved_paths
        job.generation_metadata = generation_metadata
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()

        # CRITICAL: Always unload LoRA at the end to ensure clean state for next job
        # This prevents VAE dtype issues from LoRA state persisting
        if model.current_lora is not None:
            logger.info(f"Unloading LoRA '{model.current_lora['label']}' after generation")
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
    logger.info(f"Loading model '{slug}' (cold start) - this may take several minutes for first download...")
    model_instance = ModelFactory.create_model(model_config, diffusion_model.path)

    # Progress callback for model loading
    def log_progress(progress=None, desc=None):
        if desc:
            logger.info(f"Model '{slug}': {desc}")
        elif progress is not None:
            logger.info(f"Model '{slug}': {progress}")

    result = model_instance.load_pipeline(progress_callback=log_progress)
    logger.info(f"Model '{slug}' loaded successfully: {result}")

    # Only cache if pipeline actually loaded
    if model_instance.pipeline is None:
        raise RuntimeError(f"Failed to load model '{slug}': {result}")

    _model_cache[slug] = model_instance
    return model_instance
