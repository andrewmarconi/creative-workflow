Working with LoRAs
==================

This guide covers adding, configuring, and using LoRA (Low-Rank Adaptation) models for style control in image generation.

Overview
--------

LoRAs are lightweight adapters that modify a base diffusion model's output style without retraining the full model. The system supports:

- **Architecture-based compatibility** — LoRAs are filtered to show only those compatible with the selected diffusion model
- **CivitAI auto-download** — LoRAs can be downloaded automatically from CivitAI using AIR URN identifiers
- **Per-LoRA overrides** — each LoRA can specify trigger words, strength, guidance scale, clip skip, and negative prompts
- **Theme categorization** — LoRAs can be tagged with themes for organizational filtering

Adding a LoRA via presets.json
-------------------------------

Add a LoRA entry to the ``loras`` array in ``data/presets.json``:

.. code-block:: json

   {
     "label": "Pen & Ink Illustration",
     "base_architecture": "zimage",
     "theme": "illustration",
     "air": "urn:air:zimageturbo:lora:civitai:2344335@2636956",
     "prompt": "phrsink, pen and ink illustration",
     "negative_prompt": "blurry ugly bad",
     "settings": {
       "strength": 0.7,
       "guidance_scale": 1.0,
       "clip_skip": 2
     },
     "notes": "Works best with simple compositions"
   }

Then sync to the database:

.. code-block:: bash

   uv run manage.py import_presets

Configuration Fields
^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - ``label``
     - Display name shown in the admin UI dropdown
   * - ``base_architecture``
     - Compatibility filter: ``sdxl``, ``sd15``, ``flux1``, ``qwen``, or ``zimage``
   * - ``theme``
     - Optional category for filtering (e.g., ``anime``, ``photorealistic``, ``sketch``, ``cinematic``, ``artistic``, ``illustration``)
   * - ``air``
     - CivitAI AIR URN for auto-download (see below)
   * - ``path``
     - Local path to ``.safetensors`` file, relative to ``MODEL_BASE_PATH``. Optional if ``air`` is provided.
   * - ``prompt``
     - Trigger words appended to every prompt when this LoRA is active
   * - ``negative_prompt``
     - Terms appended to the negative prompt (only for models that support negative prompts)
   * - ``settings.strength``
     - LoRA weight (0.0–2.0, typically 0.5–1.3). Higher values produce stronger style effects.
   * - ``settings.guidance_scale``
     - Override the model's default CFG when this LoRA is active
   * - ``settings.clip_skip``
     - Number of CLIP layers to skip (1–12). Common for anime/artistic styles.
   * - ``notes``
     - Usage tips or CivitAI statistics

Architecture Compatibility
--------------------------

LoRAs are only compatible with models that share their ``base_architecture``. The admin UI automatically filters the LoRA dropdown to show only compatible options.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Architecture
     - Compatible Models
     - Example LoRAs
   * - ``sdxl``
     - SDXL Turbo, Juggernaut XL, DreamShaper XL
     - Collage Art, Real Humans, LineAni.Redmond
   * - ``sd15``
     - Realistic Vision v5.1
     - Pen Sketch Style, Sketch Anime Pose
   * - ``zimage``
     - Z-Image Turbo
     - 80s Fantasy Movie, Line Drawing, Pen & Ink
   * - ``flux1``
     - Flux.1-dev, Flux 2 Klein
     - (add Flux-compatible LoRAs as they become available)
   * - ``qwen``
     - Qwen-Image-2512
     - (add Qwen-compatible LoRAs as they become available)

CivitAI Auto-Download
---------------------

LoRAs with an ``air`` (Adaptive Identifier Resource) URN are automatically downloaded from CivitAI on first use if the local file doesn't exist.

AIR URN Format
^^^^^^^^^^^^^^

.. code-block:: text

   urn:air:{ecosystem}:lora:civitai:{modelId}@{versionId}

Example: ``urn:air:zimageturbo:lora:civitai:2344335@2636956``

The system extracts the ``modelId`` and ``versionId``, fetches metadata from the CivitAI API, and downloads the ``.safetensors`` file to the local path.

Setup
^^^^^

Set the ``CIVITAI_API_KEY`` environment variable in ``.env``:

.. code-block:: text

   CIVITAI_API_KEY=your_api_key_here

Without this key, auto-downloads will fail and you'll need to place ``.safetensors`` files manually.

Download Flow
^^^^^^^^^^^^^

When a DiffusionJob uses a LoRA:

1. The task checks if the LoRA file exists at the expected local path
2. If missing and an ``air`` URN is set, the task downloads it from CivitAI
3. The download streams to a temporary file, then atomically renames to the final path
4. Metadata (trigger words, base architecture) is extracted from the CivitAI API response
5. The LoRA is loaded into the pipeline

Trigger Words
-------------

Many LoRAs require specific trigger words in the prompt to activate their style. Set these in the ``prompt`` field:

.. code-block:: json

   {
     "prompt": "phrsink, pen and ink illustration"
   }

Trigger words are **automatically appended** to the user's prompt when the LoRA is active. For CLIP-based models (SDXL, SD15), the system handles token limits — either via Compel (which has no limit) or via the legacy token limiter (which prioritizes trigger words over prompt text when truncating).

Strength and Overrides
----------------------

**Strength** controls how strongly the LoRA modifies the base model's output:

- ``0.3–0.5`` — subtle influence, base model style dominates
- ``0.6–0.8`` — balanced, noticeable style change
- ``0.9–1.2`` — strong style, LoRA dominates
- ``>1.2`` — very strong, may introduce artifacts

**Guidance scale** override replaces the model's default CFG when this LoRA is active. Some LoRAs are trained at specific CFG values and produce best results when that value is enforced.

**Clip skip** tells the model to skip layers in the CLIP text encoder. This is common for anime-style LoRAs (typically ``clip_skip: 2``) and affects how literally the model interprets the prompt.

Local File Resolution
---------------------

LoRA ``.safetensors`` files are resolved relative to the ``MODEL_BASE_PATH`` environment variable:

.. code-block:: text

   # Full path = MODEL_BASE_PATH / path
   # Example: /models/loras/pen-ink.safetensors

If ``MODEL_BASE_PATH`` is not set, paths are resolved relative to the current directory. For CivitAI auto-downloaded LoRAs, the file is saved to the path specified in the LoRA configuration.

Using LoRAs in the Admin
------------------------

1. Navigate to **Diffusion > Diffusion Jobs > Add Diffusion Job**
2. Select a **Diffusion Model**
3. The **LoRA Model** dropdown automatically filters to show only LoRAs compatible with the selected model's architecture
4. Select a LoRA and save — the job will apply the LoRA during generation
5. Trigger words, strength, and any overrides are applied automatically
