Compel Prompt Weighting
=======================

This guide covers Compel's prompt weighting syntax and long prompt support for CLIP-based diffusion models.

What Is Compel?
---------------

`Compel <https://github.com/damian0815/compel>`_ is a prompt encoding library that provides two features for CLIP-based models:

1. **Prompt weighting** — control the influence of individual concepts with ``(word:weight)`` syntax
2. **Long prompt support** — break prompts longer than 77 tokens into chunks, removing CLIP's token limit

Compel works by converting text prompts into pre-computed embeddings that are passed directly to the diffusion pipeline, bypassing CLIP's tokenizer limits.

Supported Models
----------------

Compel is available for models that use CLIP text encoders:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Model
     - Architecture
     - Compel Support
   * - Juggernaut XL v9
     - SDXL
     - Yes (dual text encoders)
   * - DreamShaper XL Lightning
     - SDXL
     - Yes (dual text encoders)
   * - SDXL Turbo
     - SDXL
     - Yes (dual text encoders)
   * - Realistic Vision v5.1
     - SD 1.5
     - Yes (single text encoder)
   * - Flux.1-dev
     - Flux
     - No (T5 text encoder)
   * - Qwen-Image-2512
     - Qwen
     - No (Qwen text encoder)
   * - Z-Image Turbo
     - ZImage
     - No (custom text encoder)

Models without Compel support use their native text encoders directly and handle long prompts via ``max_sequence_length`` configuration.

Prompt Weighting Syntax
-----------------------

Use ``(concept:weight)`` to control how strongly a concept influences the generated image:

- **Weight > 1.0** — emphasize the concept
- **Weight < 1.0** — de-emphasize the concept
- **Weight = 1.0** — default (same as no weighting)

Examples
^^^^^^^^

.. code-block:: text

   # Emphasize dramatic lighting and de-emphasize blur
   a beautiful landscape with (dramatic lighting:1.5), avoiding (blur:0.5)

   # Strong emphasis on a specific style
   portrait of a woman, (oil painting style:1.4), (soft focus:0.7)

   # Emphasize specific elements in a scene
   a cozy cafe with (warm lighting:1.3) and (steam rising from coffee:1.2)

   # Balance multiple concepts
   (photorealistic:1.3) cityscape at (golden hour:1.5), (cinematic:1.2) composition

Weight guidelines:

- **1.1–1.3** — subtle emphasis, nudges the model toward the concept
- **1.3–1.5** — noticeable emphasis, concept becomes a focal point
- **1.5–2.0** — strong emphasis, may produce exaggerated results
- **0.5–0.8** — gentle de-emphasis, concept is present but reduced
- **< 0.5** — strong de-emphasis, concept is largely suppressed

Long Prompt Support
-------------------

Without Compel, CLIP-based models truncate prompts at 77 tokens (~50–60 words). With Compel, prompts of any length work:

.. code-block:: text

   # This long prompt works without truncation on SDXL/SD15 models:
   a highly detailed, photorealistic landscape painting of a serene mountain
   valley at sunset, with dramatic lighting, golden hour atmosphere, misty
   background, lush green meadows in the foreground, snow-capped peaks in
   the distance, a winding river reflecting the warm sky colors, scattered
   wildflowers in purple and yellow, ancient pine trees framing the scene,
   wispy clouds catching the last rays of sunlight

Compel automatically chunks the prompt into 77-token segments and concatenates the resulting embeddings, preserving the full prompt content.

LoRA Integration
----------------

When a LoRA is active, its trigger words are appended to the prompt before Compel encoding. Since Compel removes the 77-token limit, trigger words are always included in full — there's no risk of them being truncated.

You can also apply weighting to LoRA trigger words:

.. code-block:: text

   a mountain landscape, (phrsink:1.2), pen and ink illustration

Practical Tips
--------------

- **Start subtle** — begin with weights of 1.1–1.3 and adjust from there
- **Don't over-weight** — values above 1.5 often produce artifacts or distorted results
- **Combine with negative prompts** — for models that support them (Juggernaut XL, Realistic Vision), negative prompts complement weighting by excluding unwanted elements
- **Test without weighting first** — generate a baseline image, then add weighting to steer specific aspects
- **Weighting doesn't work on non-CLIP models** — Flux, Qwen, and Z-Image ignore the ``(word:weight)`` syntax; the parentheses and numbers become part of the literal prompt text
