Storyboard Generation
=====================

This guide covers creating storyboards from adapted scripts — generating visual frames using diffusion models.

Overview
--------

A **Storyboard** links a ``VideoAdUnit`` to a ``DiffusionModel`` (and optional ``LoRA``) to generate one or more images per script row. The process:

1. Extract visual elements from each script row's ``visual_text``
2. Optionally enhance prompts with an LLM
3. Create ``DiffusionJob`` records for each frame
4. Queue jobs for image generation

.. mermaid::

   graph LR
       Script["Script Rows"] --> Generator["StoryboardGenerator"]
       Generator --> Prompts["Image Prompts"]
       Prompts --> Jobs["DiffusionJobs"]
       Jobs --> Images["Storyboard Frames<br/>(1280×720)"]

Creating a Storyboard
---------------------

1. Navigate to **TV Spots > Storyboards > Add Storyboard**
2. Select the **Video Ad Unit** (must have script rows)
3. Choose a **Diffusion Model** for image generation
4. Optionally select a **LoRA Model** for style control
5. Set **Images Per Row** (default: 1) — generates multiple variations per shot
6. Save — the ``generate_storyboard_task`` is automatically queued

Multiple storyboards can be created for the same ad unit with different model and LoRA configurations, allowing visual comparison across styles.

Prompt Generation
-----------------

The ``StoryboardGenerator`` converts script row visual descriptions into diffusion model prompts.

Visual Element Extraction
^^^^^^^^^^^^^^^^^^^^^^^^^

The generator processes each row's ``visual_text``:

1. **Remove timing references** — strips timecodes like ``00:00:05:00`` and duration markers like ``(5.0s)``
2. **Normalize shot types** — standardizes shot type prefixes (CU, MCU, MS, WS, ECU, etc.)
3. **Add visual style prefix** — prepends the ad unit's ``visual_style_prompt`` for consistency
4. **Add quality keywords** — appends ``cinematic still, professional photography, high quality, detailed``

Example transformation:

.. code-block:: text

   # Input (visual_text):
   Medium shot: Kitchen counter. TALENT opens refrigerator, pulls out
   ACME ENERGY DRINK can. Product hero shot with condensation.

   # Output (base prompt):
   warm cinematic lighting, MS: Kitchen counter. TALENT opens refrigerator,
   pulls out ACME ENERGY DRINK can. Product hero shot with condensation.,
   cinematic still, professional photography, high quality, detailed

LLM Enhancement
^^^^^^^^^^^^^^^

When ``enhance_prompts=True`` (the default), the generator uses the ``HFPromptEnhancer`` (Qwen2.5-3B-Instruct) to rewrite prompts with richer visual detail:

- Style-specific descriptors are added
- Scene composition is refined for diffusion model compatibility
- A negative prompt is generated to avoid common artifacts

If LLM enhancement fails, the generator falls back to the base prompt.

DiffusionJob Creation
---------------------

After prompts are generated, ``create_storyboard_jobs()`` creates the database records:

For each script row (times ``images_per_row``):

1. A **Prompt** record with the enhanced prompt and negative prompt
2. A **DiffusionJob** linked to the selected diffusion model and LoRA
3. A **StoryboardImage** linking the storyboard, script row, and diffusion job

Job identifiers follow the pattern: ``{job_id}_{ad_unit_code}_row-{NN}_img-{NN}``

All storyboard frames use **1280×720** dimensions (16:9 aspect ratio).

Task Flow
---------

The ``generate_storyboard_task`` executes these steps:

1. **Evict pipeline model** — clears the adaptation pipeline's LLM from VRAM
2. **Generate prompts** — runs ``StoryboardGenerator`` for all script rows
3. **Clear GPU cache** — frees VRAM after prompt enhancement
4. **Create jobs** — creates ``Prompt``, ``DiffusionJob``, and ``StoryboardImage`` records
5. **Queue generation** — dispatches each ``DiffusionJob`` to the ``default`` Celery queue
6. **Update status** — marks the storyboard as ``completed``

Each queued ``DiffusionJob`` is then processed by the image generation worker, which loads the diffusion model (with warm cache), optionally applies the LoRA, and generates the image.

Progress Tracking
-----------------

The ``Storyboard`` model provides three computed properties:

- ``total_jobs`` — total ``DiffusionJob`` count in this storyboard
- ``completed_jobs`` — count of jobs with ``status="completed"``
- ``progress_percent`` — completion percentage (0–100)

Status Lifecycle
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Description
   * - ``pending``
     - Storyboard created, task not yet started
   * - ``processing``
     - Prompt generation and job creation in progress
   * - ``completed``
     - All jobs created and queued (individual image generation may still be running)
   * - ``failed``
     - Error during prompt generation or job creation

Note that ``completed`` means the storyboard task itself finished — individual ``DiffusionJob`` records track their own status as images are generated.

VRAM Management
---------------

Storyboard generation involves two GPU-intensive stages that are managed sequentially:

1. **Prompt enhancement** — loads the Qwen2.5-3B LLM into VRAM
2. **Image generation** — loads the diffusion model into VRAM

The task pipeline ensures these don't compete:

- Before prompt enhancement: ``_evict_pipeline_model()`` clears the adaptation LLM
- After prompt enhancement: ``torch.mps.empty_cache()`` / ``torch.cuda.empty_cache()`` frees VRAM
- Image generation jobs run sequentially via the Celery ``solo`` pool

Viewing Storyboard Frames
--------------------------

After image generation completes:

1. Navigate to the **Storyboard** detail page
2. View **Storyboard Images** as inline entries, each showing:

   - Script row reference (shot number, order index)
   - Linked ``DiffusionJob`` with status and generated image
   - Image index (for multi-image configurations)

3. Images are sorted by script row order and image index, providing a sequential visual narrative

Comparing Configurations
^^^^^^^^^^^^^^^^^^^^^^^^

Create multiple storyboards for the same ad unit to compare:

- Different diffusion models (e.g., Juggernaut XL for photorealism vs. DreamShaper XL for stylized)
- Different LoRAs (e.g., pen-and-ink illustration vs. cinematic film)
- Different visual style prompts on the ad unit
- With and without LLM prompt enhancement
