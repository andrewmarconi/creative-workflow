Prompt Enhancement
==================

This guide covers the three prompt enhancement methods, when to use each, and how enhancement integrates with image generation.

Overview
--------

Prompt enhancement takes a user's source prompt and improves it for better diffusion model results — adding quality descriptors, style-specific tags, and technical details that diffusion models respond to.

Three methods are available, each with different tradeoffs:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Method
     - Speed
     - Quality
     - Dependencies
     - Best For
   * - **Rule-based**
     - Instant
     - Good
     - None
     - Fast prototyping, consistent results
   * - **HuggingFace**
     - ~10–30s
     - Better
     - Local GPU (3–7 GB VRAM)
     - Offline use, Apple Silicon
   * - **Anthropic API**
     - ~3–5s
     - Best
     - ``ANTHROPIC_API_KEY``
     - Production quality, nuanced prompts

Rule-Based Enhancement
----------------------

The ``PromptEnhancer`` applies predefined tags and descriptors based on the detected or selected style. No external model is needed.

How it works:

1. **Style detection** — if style is set to "auto", the enhancer scans the prompt for keywords (e.g., "photo" → Photography, "painting" → Artistic)
2. **Quality tags** — adds tags like "masterpiece", "best quality", "highly detailed"
3. **Style descriptors** — adds style-specific terms (e.g., Photography gets "sharp focus, natural lighting"; Cinematic gets "dramatic composition, film grain")
4. **Negative prompt** — generates a negative prompt with common defects to avoid
5. **Creativity scaling** — the creativity level (0.0–1.0) controls how many tags are applied

Rule-based enhancement is deterministic — the same input always produces the same output.

HuggingFace Local Model
------------------------

The ``HFPromptEnhancer`` runs a local LLM (default: Qwen2.5-3B-Instruct) to rewrite the prompt with richer detail.

**Supported models**:

- ``Qwen/Qwen2.5-3B-Instruct`` (default, 3B parameters)
- ``Qwen/Qwen2.5-7B-Instruct`` (higher quality, 7B parameters)
- ``gokaygokay/Flux-Prompt-Enhance`` (specialized for diffusion prompts)
- ``microsoft/Phi-3.5-mini-instruct`` (efficient, 3.8B parameters)

The model downloads automatically from HuggingFace on first use and is cached locally. Device detection is automatic: MPS (Apple Silicon) → CUDA → CPU.

The enhancer uses two database-backed prompt templates:

- ``prompt-enhancer-system`` — system prompt defining the enhancer's role and output format
- ``prompt-enhancer-user`` — user prompt with the source prompt and style/creativity parameters

These templates are editable in the Django admin under **Core > Prompt Templates**.

If the LLM fails to produce valid JSON output, the enhancer falls back to rule-based enhancement.

Anthropic API
-------------

The ``LLMPromptEnhancer`` uses Claude via the Anthropic API for the highest-quality enhancement.

**Setup**: Set ``ANTHROPIC_API_KEY`` in your ``.env`` file.

This method uses the same prompt templates as the HuggingFace enhancer (``prompt-enhancer-system`` and ``prompt-enhancer-user``), so customizations apply to both.

The creativity parameter maps to the API's temperature setting: lower creativity produces more conservative enhancements, higher values produce more creative interpretations.

If the API call fails, the enhancer falls back to rule-based enhancement.

Style Options
-------------

Six enhancement styles control the aesthetic direction:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Style
     - Effect
   * - **Auto-detect**
     - Scans prompt keywords to choose the best style automatically
   * - **Photography**
     - Sharp focus, natural lighting, photorealistic detail
   * - **Artistic**
     - Painterly quality, expressive brushwork, creative composition
   * - **Realistic**
     - Hyperrealistic rendering, fine detail, physical accuracy
   * - **Cinematic**
     - Dramatic composition, film grain, anamorphic depth of field
   * - **Coloring Book**
     - Clean line art, flat colors, no shading — designed for printable coloring pages

Creativity Level
----------------

The creativity parameter (0.0–1.0) controls enhancement intensity:

- **0.0–0.3** — conservative, minimal additions, stays close to the original prompt
- **0.4–0.6** — moderate, adds quality tags and style descriptors
- **0.7** (default) — balanced, good mix of original intent and enhancement
- **0.8–1.0** — creative, adds more descriptors and may reinterpret the prompt

For rule-based enhancement, creativity affects how many tags from each category are applied. For LLM-based methods, it maps to the model's temperature parameter.

Integration with DiffusionJob
-----------------------------

Enhancement runs as part of the image generation pipeline:

1. User creates a **Prompt** with a source prompt, enhancement method, style, and creativity
2. User creates a **DiffusionJob** linked to that prompt
3. When the job executes, the Celery task checks if the prompt has been enhanced
4. If enhancement is needed, it runs the selected method and saves the result to ``enhanced_prompt``
5. The generation step uses ``enhanced_prompt`` if available, otherwise falls back to ``source_prompt``

VRAM Management
^^^^^^^^^^^^^^^

The HuggingFace enhancer loads a 3–7 GB LLM into GPU memory. Since the diffusion model also needs GPU memory, the system manages this automatically:

- The enhancer LLM is cached between enhancement tasks (warm cache)
- Before loading a diffusion model, the worker calls ``_evict_enhancer()`` to free VRAM
- This ensures enhancement and generation don't compete for GPU memory
- The Celery ``solo`` pool (single-threaded worker) guarantees sequential execution

Configuring Enhancement
-----------------------

When creating a Prompt in the admin UI:

1. Enter your **Source Prompt**
2. Set **Enhancement Method** to rule-based, HuggingFace, or LLM
3. Optionally set **Enhancement Style** (default: auto-detect)
4. Optionally adjust **Creativity** (default: 0.7)
5. Save — enhancement runs when the linked DiffusionJob executes

The enhanced prompt and generated negative prompt are saved to the Prompt record and visible on its detail page.
