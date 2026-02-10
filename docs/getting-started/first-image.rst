Your First Image
================

This tutorial walks you through generating your first diffusion image. By the end, you'll have a generated image viewable in the admin UI.

.. note::

   Make sure you've completed :doc:`installation` and have all services running via ``./start.sh``.

Overview
--------

The image generation workflow has three steps:

1. **Create a Prompt** — describe what you want to generate
2. **Create a DiffusionJob** — select a model and link it to your prompt
3. **View the result** — the job auto-queues to Celery and generates the image

Step 1: Create a Prompt
-----------------------

Navigate to **Diffusion > Prompts > Add Prompt** in the app.

Fill in the following:

**Source Prompt** (required)
   The text description of what you want to generate. For example::

      A serene mountain landscape at golden hour, dramatic lighting,
      snow-capped peaks reflected in a still alpine lake

That's the only required field. You can optionally configure prompt enhancement:

**Enhancement Method** (optional)
   Choose how the prompt gets enhanced before generation:

   - *No Enhancement* (default) — uses your prompt as-is
   - *Rule-based* — adds quality tags and style descriptors automatically
   - *HuggingFace Local Model* — enhances via Qwen2.5-3B running locally
   - *LLM API* — highest quality, requires ``ANTHROPIC_API_KEY`` in ``.env``

**Enhancement Style** (optional)
   If using enhancement: *Auto-detect*, *Photography*, *Artistic*, *Realistic*, *Cinematic*, or *Coloring Book*.

**Creativity** (optional)
   Controls enhancement intensity from 0.0 (conservative) to 1.0 (creative). Default: 0.7.

Click **Save**. If you chose an enhancement method, the enhanced prompt will be generated when the job runs.

Step 2: Create a DiffusionJob
-----------------------------

Navigate to **Diffusion > Diffusion Jobs > Add Diffusion Job**.

Fill in the **Configuration** tab:

**Diffusion Model** (required)
   Select the model to use. Good choices for a first run:

   - **SDXL Turbo** — fastest (4 steps), good for quick tests
   - **Flux.1-dev** — high quality (28 steps), slower but excellent results
   - **Juggernaut XL v9** — photorealistic (30 steps), supports negative prompts

**Prompt** (required)
   Select the prompt you just created from the dropdown.

**Identifier** (optional)
   A friendly name like ``my-first-image``. Used in the output filename.

**LoRA Model** (optional)
   Apply a style modifier. The dropdown is filtered to show only LoRAs compatible with your selected model's architecture.

Leave the **Parameters** tab at defaults for your first run — each model has sensible defaults configured in ``presets.json`` (steps, guidance scale, dimensions).

Click **Save**.

Step 3: Watch It Generate
-------------------------

When you save, the job is **automatically queued** to Celery. You don't need to do anything else.

You can monitor progress in two ways:

- **Flower** at http://localhost:5555 — shows the task in the active/completed list
- **Job detail page** — refresh the page to see status updates (pending → queued → processing → completed)

The first run for a given model will be slower because it downloads the model weights from HuggingFace. Subsequent runs use the cached model.

Step 4: View the Result
-----------------------

Once the job status shows **completed**, the detail page displays:

**Results tab**
   - Thumbnail previews of all generated images (clickable to view full size)
   - Images are saved to ``media/diffusion/``

**Generation Metadata**
   A JSON panel showing the exact parameters used: resolved prompt, model, steps, guidance scale, seed, LoRA details, and timing.

Experimenting Further
---------------------

Now that you have the basics, try:

- **Different models** — compare SDXL Turbo (speed) vs. Flux.1-dev (quality) vs. Juggernaut XL (photorealism)
- **Prompt enhancement** — enable rule-based or LLM enhancement and compare the enhanced prompt to your original
- **LoRAs** — apply a style LoRA (anime, photorealistic, fantasy) to the same prompt and see how it changes
- **Multiple images** — set ``num_images`` to 3 or 4 on the Parameters tab to generate variations with different seeds
- **Negative prompts** — for models that support them (Juggernaut, Realistic Vision, Qwen), add negative prompts to exclude unwanted elements
- **Compel weighting** — on SDXL/SD15 models, use ``(dramatic lighting:1.5)`` syntax to emphasize concepts

Next Steps
----------

- :doc:`first-adaptation` — Create your first culturally adapted TV spot with the multi-agent pipeline
