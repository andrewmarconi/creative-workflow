Diffusion Models
================

This page explains how the diffusion model system is designed: the Template Method pattern, mixins, factory dispatch, warm caching, and device optimization.

Design Goals
------------

The model system was designed around three constraints:

1. **One model at a time** — GPU memory is limited. Only one diffusion model can be loaded at once. You don't need a mountain of H200s to run this framework. I use a stock NVIDIA RX 3080 and a Mac M4 as two of my workstations.
2. **Minimal per-model code** — Adding a new model should take 10-20 lines, not 200.
3. **Configuration-driven behavior** — Model quirks (turbo guidance overrides, token limits, 8-bit quantization) are controlled by flags in the data model (seeded with ``presets.json``), not by branching code paths.

Template Method Pattern
-----------------------

All diffusion models inherit from ``BaseModel``, which provides two **template methods** — concrete methods that define the overall algorithm and call abstract or optional hooks for customization:

.. mermaid::

   classDiagram
       class BaseModel {
           <<abstract>>
           +load_pipeline() : Template Method
           +generate() : Template Method
           #_create_pipeline()* : Abstract Hook
           #_build_prompts() : Optional Hook
           #_build_pipeline_kwargs() : Optional Hook
           #_apply_device_optimizations() : Optional Hook
           #_handle_special_prompt_requirements() : Optional Hook
       }
       class CompelPromptMixin {
           #_build_prompts() override
           -_get_compel()
       }
       class CLIPTokenLimitMixin {
           #_build_prompts() override
           -_fit_prompt_to_token_limit()
       }
       class DebugLoggingMixin {
           #_debug_print()
       }
       class FluxModel {
           #_create_pipeline()
       }
       class SDXLModel {
           #_create_pipeline()
       }
       class SD15Model {
           #_create_pipeline()
       }
       class QwenImageModel {
           #_create_pipeline()
           #_build_pipeline_kwargs()
           #_handle_special_prompt_requirements()
       }

       BaseModel <|-- FluxModel
       BaseModel <|-- QwenImageModel
       CompelPromptMixin <|-- SDXLModel
       BaseModel <|-- SDXLModel
       CompelPromptMixin <|-- SD15Model
       BaseModel <|-- SD15Model

``load_pipeline()``
^^^^^^^^^^^^^^^^^^^

The loading template method runs three steps:

1. **Device setup** — detect MPS (Apple Silicon), CUDA, or CPU
2. **Pipeline creation** — calls ``_create_pipeline()`` (the one abstract method each model must implement)
3. **Device optimizations** — calls ``_apply_device_optimizations()`` for CPU offloading, attention slicing, and VAE fixes

``generate()``
^^^^^^^^^^^^^^

The generation template method runs six steps:

1. **Scheduler override** — apply per-job scheduler if specified
2. **Parameter preparation** — resolve defaults, apply LoRA overrides, handle ``force_default_guidance`` flag
3. **Prompt building** — calls ``_build_prompts()`` to append LoRA trigger words and handle token limits
4. **Pipeline kwargs** — calls ``_build_pipeline_kwargs()`` for model-specific parameters
5. **Image generation** — calls the pipeline and returns the first image
6. **Cleanup** — clears device memory cache and builds metadata

Hook Methods
^^^^^^^^^^^^

Concrete models customize behavior by overriding these hooks:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Hook
     - Purpose
   * - ``_create_pipeline()``
     - **Required.** Return the loaded pipeline instance (e.g., ``FluxPipeline.from_pretrained(...)``)
   * - ``_build_prompts(params)``
     - Customize prompt processing. Default appends LoRA suffix. Overridden by ``CompelPromptMixin`` and ``CLIPTokenLimitMixin``.
   * - ``_build_pipeline_kwargs(params, callback)``
     - Add model-specific kwargs. Default builds standard kwargs. Overridden by ``QwenImageModel`` (runtime parameter detection).
   * - ``_apply_device_optimizations()``
     - Custom device setup. Default handles MPS VAE float32 fix, CPU offloading, attention slicing.
   * - ``_handle_special_prompt_requirements(params)``
     - Model-specific prompt quirks. Overridden by ``QwenImageModel`` (requires space for empty negative prompt).

Mixins
------

Shared behaviors are composed via multiple inheritance. Mixins must be listed **before** ``BaseModel`` in the class definition to properly override hooks via Python's MRO (Method Resolution Order).

CompelPromptMixin
^^^^^^^^^^^^^^^^^

Used by SDXL and SD15 models for advanced prompt handling via the `Compel <https://github.com/damian0815/compel>`_ library:

- **Long prompts** — breaks prompts longer than 77 tokens into chunks and concatenates the embeddings, removing the CLIP token limit
- **Prompt weighting** — ``(dramatic lighting:1.5)`` syntax to emphasize or de-emphasize concepts
- **LoRA integration** — trigger words appended without truncation concerns
- **Dual text encoder support** — automatically detects and handles SDXL's two text encoders

The mixin overrides ``_build_prompts()`` to convert text into pre-computed embeddings (``prompt_embeds``), which are passed directly to the pipeline instead of raw text.

CLIPTokenLimitMixin (Legacy)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The original approach to CLIP's 77-token limit. Truncates prompts to fit within the token budget while prioritizing LoRA trigger words. Superseded by ``CompelPromptMixin`` for new models, but still available.

DebugLoggingMixin
^^^^^^^^^^^^^^^^^

Provides a ``_debug_print()`` method gated behind the ``enable_debug_logging`` configuration flag. Used by turbo models for diagnostic output during development.

Concrete Models
---------------

Each concrete model is a thin subclass — typically 20–70 lines — that only overrides what differs from the base:

.. list-table::
   :header-rows: 1
   :widths: 20 20 15 10 35

   * - Model
     - Pipeline
     - Parents
     - Lines
     - Key Overrides
   * - **ZImageTurboModel**
     - ``ZImagePipeline``
     - DebugLogging + Base
     - ~108
     - Custom device optimizations, step callback, LoRA VAE fixes
   * - **FluxModel**
     - ``FluxPipeline``
     - Base only
     - ~22
     - ``_create_pipeline()`` only — minimal implementation
   * - **QwenImageModel**
     - ``QwenImagePipeline``
     - Base only
     - ~87
     - 8-bit quantization, runtime ``true_cfg_scale`` detection, empty-negative-prompt fix
   * - **SDXLModel**
     - ``StableDiffusionXLPipeline``
     - CLIPTokenLimit + Base
     - ~52
     - Token-limited prompts, negative prompt support, LoRA VAE fixes
   * - **SDXLTurboModel**
     - ``StableDiffusionXLPipeline``
     - CLIPTokenLimit + DebugLogging + Base
     - ~99
     - Token limit with debug logging, custom MPS optimizations
   * - **SD15Model**
     - ``StableDiffusionPipeline``
     - CLIPTokenLimit + Base
     - ~51
     - Token-limited prompts, negative prompt support, LoRA VAE fixes

A minimal model implementation looks like this:

.. code-block:: python

   from diffusers import FluxPipeline
   from .base import BaseModel

   class FluxModel(BaseModel):
       def _create_pipeline(self):
           return FluxPipeline.from_pretrained(
               self.model_path,
               torch_dtype=self.dtype,
           )

Everything else — device setup, generation loop, LoRA management, metadata building, cache clearing — is inherited from ``BaseModel``.

ModelFactory
------------

``ModelFactory.create_model()`` dispatches on the ``pipeline`` field from ``presets.json``:

.. list-table::
   :header-rows: 1
   :widths: 40 30

   * - Pipeline Name
     - Model Class
   * - ``ZImagePipeline``
     - ``ZImageTurboModel``
   * - ``FluxPipeline``
     - ``FluxModel``
   * - ``QwenImagePipeline``
     - ``QwenImageModel``
   * - ``AutoPipelineForText2Image``
     - ``SDXLTurboModel``
   * - ``StableDiffusionXLPipeline``
     - ``SDXLModel``
   * - ``StableDiffusionPipeline``
     - ``SD15Model``

Configuration Flags
-------------------

Model behavior is driven by flags in ``data/presets.json`` under each model's ``settings`` block:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Flag
     - Effect
   * - ``force_default_guidance``
     - Always use the model's default ``guidance_scale``, ignoring user overrides. Used by turbo models that require CFG 0.0.
   * - ``max_sequence_length``
     - Maximum text encoder context length. ``512`` for Flux, ``256`` for Flux 2 Klein.
   * - ``load_in_8bit``
     - Enable 8-bit quantization for reduced VRAM usage. Supported by QwenImageModel.
   * - ``use_sequential_cpu_offload``
     - Use ``enable_sequential_cpu_offload()`` instead of ``enable_model_cpu_offload()``. More memory-efficient but slower.
   * - ``enable_vae_slicing``
     - Process VAE decode in slices for lower peak memory usage.
   * - ``enable_debug_logging``
     - Enable verbose debug output via ``DebugLoggingMixin``.
   * - ``supports_negative_prompt``
     - Whether the model accepts negative prompts. Juggernaut XL, Realistic Vision, and Qwen support this.
   * - ``scheduler``
     - Default scheduler class name (e.g., ``EulerDiscreteScheduler``). Can be overridden per job.

Warm Cache
----------

The Celery worker maintains a **module-level model cache** — a dictionary that keeps the most recently used model loaded in memory:

.. code-block:: python

   _model_cache = {}  # {slug: model_instance}

This is safe because Celery is configured with the ``solo`` pool (single-threaded worker). The cache works as follows:

1. A generation task calls ``_load_model_instance(diffusion_model)``
2. If the requested model slug matches the cached model and its pipeline is loaded, the cached instance is returned immediately (warm hit)
3. If a different model is cached, it is **evicted** — its pipeline is deleted and the device cache is cleared (``torch.mps.empty_cache()`` or ``torch.cuda.empty_cache()``)
4. The new model is instantiated via ``ModelFactory``, its pipeline is loaded, and it replaces the evicted model in the cache

This ensures:

- **No redundant loading** — consecutive jobs using the same model skip pipeline loading entirely
- **One model at a time** — only one diffusion model occupies GPU memory at any given moment
- **Clean transitions** — eviction explicitly frees device memory before loading the next model

Before loading any diffusion model, the worker also calls ``_evict_enhancer()`` to free VRAM occupied by the prompt enhancement LLM or the adaptation pipeline's LLM, preventing out-of-memory errors.

Device Optimization
-------------------

``BaseModel._apply_device_optimizations()`` handles three device targets:

**MPS (Apple Silicon)**
   - VAE converted to ``float32`` (prevents NaN values in bfloat16 VAE on MPS)
   - Entire pipeline moved to MPS device
   - Attention slicing enabled
   - VAE slicing and tiling enabled for memory efficiency

**CUDA**
   - ``enable_model_cpu_offload()`` by default (or ``enable_sequential_cpu_offload()`` if the flag is set)
   - Attention slicing enabled

**CPU**
   - Pipeline moved to CPU (fallback, no optimizations)

Individual models can override ``_apply_device_optimizations()`` for model-specific needs. For example, ``ZImageTurboModel`` adds sequential CPU offload and VAE slicing on CUDA, while ``SDXLTurboModel`` has a custom MPS optimization path.

Model Comparison
----------------

.. list-table::
   :header-rows: 1
   :widths: 18 8 8 8 14 14

   * - Model
     - Steps
     - CFG
     - Resolution
     - Architecture
     - Best For
   * - Z-Image Turbo
     - 9
     - 0.0
     - 1024
     - zimage
     - Fast iteration, drafts
   * - Flux.1-dev
     - 28
     - 3.5
     - 1024
     - flux1
     - High quality, presentation
   * - Qwen-Image
     - 50
     - 4.5
     - 1328
     - qwen
     - Photorealism, fine detail
   * - SDXL Turbo
     - 4
     - 0.0
     - 512
     - sdxl
     - Fastest, quick tests
   * - Juggernaut XL v9
     - 30
     - 7.0
     - 1024
     - sdxl
     - Photorealism, negative prompts
   * - DreamShaper XL
     - 4
     - 2.0
     - 1024
     - sdxl
     - Fast creative, artistic
   * - Realistic Vision v5.1
     - 30
     - 5.0
     - 512x768
     - sd15
     - Portraits, low VRAM

Adding a New Model
------------------

For most models, this takes four steps:

1. **Create the model file** — inherit from ``BaseModel`` and override ``_create_pipeline()``
2. **Register in the factory** — add to ``ModelFactory.create_model()`` in ``src/cw/lib/models/__init__.py``
3. **Add to presets** — add a model entry in ``data/presets.json`` with appropriate settings flags
4. **Sync to database** — run ``uv run manage.py import_presets``

If the model uses CLIP-based text encoding (SDXL/SD15 family), inherit from ``CompelPromptMixin`` for long prompt support and prompt weighting. If the model has unusual requirements (runtime parameter detection, special prompt handling), override the relevant hook methods.
