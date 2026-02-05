Model Reference
===============

Overview of available diffusion models and their creative characteristics.

Model Palette
-------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 25 10 15

   * - Model
     - Architecture
     - Creative Character
     - Speed
     - Style Flexibility
   * - Z-Image Turbo
     - Lumina/S3-DiT
     - Rapid ideation
     - Fast
     - Moderate
   * - Flux.1-dev
     - Flux.1
     - Balanced creation
     - Medium
     - High
   * - Flux.2 Klein
     - Flux.1
     - Lightweight exploration
     - Medium
     - High
   * - SDXL Turbo
     - SDXL
     - Fast prototyping
     - Fast
     - Moderate
   * - Juggernaut XL v9
     - SDXL
     - Photorealistic detail
     - Slow
     - Very High
   * - DreamShaper XL Lightning
     - SDXL
     - Stylized speed
     - Fast
     - High
   * - Realistic Vision v5.1
     - SD 1.5
     - Classic photorealism
     - Slow
     - Very High

Creative Strategies by Model
----------------------------

**Rapid Iteration**
    Use Z-Image Turbo or SDXL Turbo for quick concept exploration. These models
    generate in 4-9 steps, allowing fast iteration on prompt ideas before
    committing to longer generation times.

**Balanced Creation**
    Flux.1-dev and Flux.2 Klein offer a good balance between speed and quality
    for general creative work. They handle complex prompts well and produce
    consistent results.

**Detailed Refinement**
    Juggernaut XL v9 and Realistic Vision v5.1 excel at photorealistic output
    with fine detail. Use these for final renders once you've refined your
    prompt through faster models.

**Stylized Experimentation**
    DreamShaper XL Lightning combines speed with artistic flexibility. Good for
    exploring different visual styles without long wait times.

Architecture Compatibility
--------------------------

LoRAs and model extensions are architecture-specific:

**SDXL Architecture**
    - Juggernaut XL v9
    - DreamShaper XL Lightning
    - SDXL Turbo

**SD 1.5 Architecture**
    - Realistic Vision v5.1

**Flux.1 Architecture**
    - Flux.1-dev
    - Flux.2 Klein

**Lumina/S3-DiT Architecture**
    - Z-Image Turbo

When selecting LoRAs, ensure the ``base_architecture`` matches your target model.
The admin interface automatically filters compatible LoRAs.

Model-Specific Notes
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 12 10 8 15 20

   * - Model
     - Pipeline
     - Steps
     - CFG
     - Negative Prompt
     - Notes
   * - Z-Image Turbo
     - ZImagePipeline
     - 9
     - 0.0
     - No
     - Turbo model, ignores CFG
   * - Flux.1-dev
     - FluxPipeline
     - 28
     - 3.5
     - No
     - High quality, longer context
   * - Flux.2 Klein
     - FluxPipeline
     - 28
     - 3.5
     - No
     - Smaller, faster Flux variant
   * - SDXL Turbo
     - AutoPipeline
     - 4
     - 0.0
     - No
     - Turbo model, ignores CFG
   * - Juggernaut XL v9
     - SDXL Pipeline
     - 30
     - 7.0
     - Yes
     - Photorealistic specialist
   * - DreamShaper XL
     - SDXL Pipeline
     - 4
     - 2.0
     - No
     - Lightning distillation
   * - Realistic Vision
     - SD Pipeline
     - 30
     - 5.0
     - Yes
     - Classic SD 1.5

Prompt Tips by Architecture
---------------------------

**SDXL and SD 1.5 Models**
    These models use CLIP text encoders with a 77-token context window.
    Generative Creative Lab uses Compel for automatic prompt chunking, so long
    prompts work without truncation. You can also use prompt weighting syntax::

        a (beautiful:1.3) landscape with (dramatic lighting:1.5)

**Flux Models**
    Flux models have longer context windows (256-512 tokens) and understand
    natural language well. Write descriptive prompts without special syntax.

**Turbo Models**
    Turbo models (Z-Image, SDXL Turbo, DreamShaper Lightning) work best with
    shorter, focused prompts. They don't benefit from negative prompts.

See :doc:`adding-models` for information on adding new models to the framework.
