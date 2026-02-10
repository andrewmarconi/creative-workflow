Pipeline Settings
=================

This guide covers the PipelineSettings singleton — the app-level configuration for adaptation pipeline model defaults.

Overview
--------

**PipelineSettings** is a singleton model (always ``pk=1``) that provides default LLM model assignments for each pipeline node. These defaults apply to all adaptations unless overridden at the ad unit level.

Accessing PipelineSettings
--------------------------

1. Navigate to **Core > Pipeline Settings** in the admin
2. There is exactly one record — click to edit

If no record exists, one is created automatically when first accessed (via ``PipelineSettings.get_instance()``).

Configurable Fields
-------------------

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Field
     - Pipeline Node
     - Description
   * - **Global Default Model**
     - All nodes (fallback)
     - Used when no node-specific default is set
   * - **Concept Default Model**
     - Concept Analyst
     - Extracts themes from origin script
   * - **Culture Default Model**
     - Cultural Researcher
     - Produces cultural brief for target market
   * - **Format Gate Default Model**
     - Format Evaluator
     - Checks language compliance
   * - **Culture Gate Default Model**
     - Cultural Evaluator
     - Validates cultural sensitivity
   * - **Concept Gate Default Model**
     - Concept Evaluator
     - Verifies concept preservation
   * - **Brand Gate Default Model**
     - Brand Evaluator
     - Checks brand consistency

Note that the **writer** node is intentionally excluded — it defaults to the language's primary model instead, since it produces target-language content. Override the writer via the ad unit's ``pipeline_model_config`` if needed.

All fields are optional ForeignKeys to ``LLMModel``. If left blank, the node falls through to the global default model, and then to the language's primary model.

How Settings Interact with Overrides
-------------------------------------

PipelineSettings sits in the middle of the model resolution chain:

.. code-block:: text

   Ad Unit override        ← highest priority
     ↓
   PipelineSettings node default
     ↓
   PipelineSettings global default
     ↓
   Language primary model   ← lowest priority

This means:

- **PipelineSettings** sets the baseline for all adaptations
- **Ad unit overrides** can change individual nodes for specific adaptations
- **Language primary model** is the ultimate fallback if nothing else is configured

See :doc:`per-node-models` for the full resolution chain and examples.

Configuration Strategies
------------------------

Uniform Model
^^^^^^^^^^^^^

Set only the **Global Default Model** and leave all node-specific fields blank. Every node uses the same model:

- Simple to manage
- Good starting point
- All nodes share the same quality/speed tradeoff

Split by Role
^^^^^^^^^^^^^

Assign different models based on node role:

- **Analysis nodes** (concept, culture) — use a model strong in reasoning and cultural knowledge
- **Evaluation nodes** (format, cultural, concept, brand gates) — use a model strong in structured evaluation
- **Writer node** — handled by language primary model (no PipelineSettings field)

This balances quality where it matters most (evaluation gates) with efficiency elsewhere.

Quality vs. Speed
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Approach
     - Model Choice
     - Tradeoff
   * - **Maximum quality**
     - Qwen2.5-7B for all nodes
     - Slower, more VRAM, better evaluation accuracy
   * - **Balanced**
     - 7B for evaluators, 3B for analysis
     - Good quality with reasonable speed
   * - **Maximum speed**
     - Qwen2.5-3B for all nodes
     - Fastest, lowest VRAM, may miss nuanced issues
   * - **4-bit quantized**
     - Any model with ``load_in_4bit=True``
     - Reduces VRAM by ~50%, slight quality loss

Editing in the Admin
--------------------

1. Navigate to **Core > Pipeline Settings**
2. Click the settings record
3. For each node, select an LLM model from the dropdown (or leave blank for fallback)
4. Set the **Global Default Model** — this is the baseline for unconfigured nodes
5. Save

Changes take effect immediately for new adaptation tasks. Running tasks continue with their already-resolved models.

LLM Models
----------

Available LLM models are managed under **Core > LLM Models**. Each model has:

- **Model ID** — HuggingFace model identifier (e.g., ``Qwen/Qwen2.5-7B-Instruct``)
- **Name** — display name
- **Load in 4-bit** — whether to use 4-bit quantization (requires ``bitsandbytes``)
- **Is Active** — only active models appear in PipelineSettings dropdowns

To add a new model, create an LLMModel record and it becomes available for selection in both PipelineSettings and per-ad-unit overrides.
