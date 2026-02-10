Model Specifications
====================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

Technical specifications for all supported diffusion models.

Planned content:

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * - Model
     - Pipeline
     - Steps
     - CFG
     - Neg. Prompt
     - Architecture
   * - Z-Image Turbo
     - ZImagePipeline
     - 9
     - 0.0
     - No
     - zimage
   * - Flux.1-dev
     - FluxPipeline
     - 28
     - 3.5
     - No
     - flux1
   * - Qwen-Image-2512
     - QwenImagePipeline
     - 50
     - 4.5
     - Yes
     - qwen
   * - SDXL Turbo
     - AutoPipeline
     - 4
     - 0.0
     - No
     - sdxl
   * - Juggernaut XL v9
     - SDXL Pipeline
     - 30
     - 7.0
     - Yes
     - sdxl
   * - DreamShaper XL
     - SDXL Pipeline
     - 4
     - 2.0
     - No
     - sdxl
   * - Realistic Vision v5.1
     - SD Pipeline
     - 30
     - 5.0
     - Yes
     - sd15

Additional details per model: VRAM requirements, dtype, scheduler, Compel support, recommended use cases.
