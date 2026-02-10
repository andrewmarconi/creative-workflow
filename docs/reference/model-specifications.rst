Model Specifications
====================

Technical specifications for all supported diffusion models.

Summary Table
-------------

.. list-table::
   :header-rows: 1
   :widths: 18 20 6 6 6 8 8

   * - Model
     - Pipeline
     - Steps
     - CFG
     - Neg. Prompt
     - Architecture
     - VRAM
   * - Z-Image Turbo
     - ZImagePipeline
     - 9
     - 0.0
     - No
     - zimage
     - 8 GB
   * - Flux.1 Dev
     - FluxPipeline
     - 28
     - 3.5
     - No
     - flux1
     - 24 GB
   * - Qwen-Image-2512
     - QwenImagePipeline
     - 50
     - 4.5
     - Yes
     - qwen
     - 24 GB
   * - SDXL Turbo
     - AutoPipelineForText2Image
     - 4
     - 0.0
     - No
     - sdxl
     - 6 GB
   * - Juggernaut XL v9
     - StableDiffusionXLPipeline
     - 30
     - 7.0
     - Yes
     - sdxl
     - 8 GB
   * - DreamShaper XL Lightning
     - StableDiffusionXLPipeline
     - 4
     - 2.0
     - No
     - sdxl
     - 8 GB
   * - Realistic Vision v5.1
     - StableDiffusionPipeline
     - 30
     - 5.0
     - Yes
     - sd15
     - 4 GB

Z-Image Turbo
--------------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``zimageturbo``
   * - HuggingFace
     - ``Tongyi-MAI/Z-Image-Turbo``
   * - Architecture
     - ``zimage``
   * - Scheduler
     - FlowMatchEulerDiscreteScheduler
   * - Dtype
     - bfloat16
   * - Default Size
     - 1024 x 1024 (max 1 MP)
   * - Token Window
     - 512
   * - Prompt Handling
     - Custom (LoRA trigger word appending)
   * - LoRA Support
     - Yes (zimage architecture)

**Behavior flags**: ``force_default_guidance`` --- ignores user CFG, always uses 0.0.

Fast single-step turbo model with 9-step generation. Best for rapid prototyping and previews.

Flux.1 Dev
----------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``flux1_dev``
   * - HuggingFace
     - ``black-forest-labs/FLUX.1-dev``
   * - Architecture
     - ``flux1``
   * - Scheduler
     - FlowMatchEulerDiscreteScheduler
   * - Dtype
     - bfloat16
   * - Default Size
     - 1024 x 1024 (max 2 MP)
   * - Token Window
     - 512 (``max_sequence_length``)
   * - Prompt Handling
     - Native (no truncation)
   * - LoRA Support
     - Yes (flux1 architecture)

High-quality generation with 28 steps. Supports long prompts up to 512 tokens without truncation. Best for production-quality images.

Qwen-Image-2512
----------------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``qwen_image``
   * - HuggingFace
     - ``Qwen/Qwen-Image-2512``
   * - Architecture
     - ``qwen``
   * - Scheduler
     - FlowMatchEulerDiscreteScheduler
   * - Dtype
     - bfloat16
   * - Default Size
     - 1328 x 1328 (max 14 MP)
   * - Token Window
     - 512
   * - Prompt Handling
     - Native (requires non-empty negative prompt)
   * - LoRA Support
     - No

**Optional flag**: ``load_in_8bit`` --- enables 8-bit quantization to reduce VRAM usage.

Highest resolution model with 50-step generation. Supports negative prompts and VAE slicing for memory efficiency. Best for high-resolution outputs.

SDXL Turbo
-----------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``sdxl_turbo``
   * - HuggingFace
     - ``stabilityai/sdxl-turbo``
   * - Architecture
     - ``sdxl``
   * - Scheduler
     - EulerAncestralDiscreteScheduler
   * - Dtype
     - float16
   * - Default Size
     - 512 x 512 (max 256 KP)
   * - Token Window
     - 77 (CLIP)
   * - Prompt Handling
     - CLIPTokenLimitMixin (77-token truncation)
   * - LoRA Support
     - Yes (sdxl architecture)

**Behavior flags**: ``force_default_guidance`` --- ignores user CFG, always uses 0.0.

Ultra-fast 4-step generation at 512px. Best for quick iterations and testing LoRA effects.

Juggernaut XL v9
-----------------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``juggernaut_xl``
   * - HuggingFace
     - ``RunDiffusion/Juggernaut-XL-v9``
   * - Architecture
     - ``sdxl``
   * - Scheduler
     - DPMSolverMultistepScheduler
   * - Dtype
     - float16
   * - Default Size
     - 1024 x 1024 (max 1 MP)
   * - Token Window
     - 77 (CLIP)
   * - Prompt Handling
     - CLIPTokenLimitMixin (77-token truncation)
   * - LoRA Support
     - Yes (sdxl architecture)

Full SDXL model with 30-step generation and high CFG (7.0). Supports negative prompts. Best for photorealistic outputs and character work.

DreamShaper XL Lightning
-------------------------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``dreamshaper_xl``
   * - HuggingFace
     - ``Lykon/dreamshaper-xl-lightning``
   * - Architecture
     - ``sdxl``
   * - Scheduler
     - DPMSolverMultistepScheduler
   * - Dtype
     - float16
   * - Default Size
     - 1024 x 1024 (max 1 MP)
   * - Token Window
     - 77 (CLIP)
   * - Prompt Handling
     - CLIPTokenLimitMixin (77-token truncation)
   * - LoRA Support
     - Yes (sdxl architecture)

Distilled SDXL model with 4-step generation at full 1024px resolution. Best for fast SDXL-quality output without turbo limitations.

Realistic Vision v5.1
----------------------

.. list-table::
   :widths: 25 75

   * - Slug
     - ``realistic_vision``
   * - HuggingFace
     - ``SG161222/Realistic_Vision_V5.1_noVAE``
   * - Architecture
     - ``sd15``
   * - Scheduler
     - DPMSolverMultistepScheduler
   * - Dtype
     - float16
   * - Default Size
     - 512 x 768 (max 384 KP)
   * - Token Window
     - 77 (CLIP)
   * - Prompt Handling
     - CLIPTokenLimitMixin (77-token truncation)
   * - LoRA Support
     - Yes (sd15 architecture)

SD 1.5 model with 30-step generation. Supports negative prompts. Lowest VRAM requirement (4 GB). Best for photorealistic portraits and scenes at standard definition.

Architecture Compatibility
--------------------------

LoRAs must match the model's ``base_architecture``:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Architecture
     - Models
     - LoRA Compatibility
   * - ``sdxl``
     - SDXL Turbo, Juggernaut XL, DreamShaper XL
     - SDXL LoRAs only
   * - ``sd15``
     - Realistic Vision
     - SD 1.5 LoRAs only
   * - ``flux1``
     - Flux.1 Dev
     - Flux LoRAs only
   * - ``zimage``
     - Z-Image Turbo
     - Z-Image LoRAs only
   * - ``qwen``
     - Qwen-Image-2512
     - No LoRA support

Token Handling
--------------

CLIP-based models (SDXL, SD15) use ``CLIPTokenLimitMixin`` which truncates prompts to 77 tokens. When a LoRA is active, trigger words are prioritized --- the base prompt is trimmed to make room for trigger words within the 77-token limit.

Flux and Qwen models support 512-token prompts natively without truncation.

See :doc:`/guides/image-generation/compel-weighting` for advanced prompt weighting syntax on CLIP-based models.

Device Optimizations
--------------------

All models apply device-specific optimizations:

- **Apple Silicon (MPS)**: Sequential CPU offload, attention slicing, VAE kept in float32
- **CUDA**: Model-level CPU offload (or sequential with ``use_sequential_cpu_offload`` flag)
- **CPU**: Fallback with no optimizations
