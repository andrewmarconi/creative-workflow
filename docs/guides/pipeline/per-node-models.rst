Per-Node Model Selection
========================

This guide explains how to assign different LLM models to individual pipeline nodes, allowing fine-grained control over quality and speed.

Model Resolution Chain
----------------------

Each pipeline node resolves its LLM model through a fallback chain. The first match wins:

**Non-writer nodes** (concept, culture, format_eval, cultural_eval, concept_eval, brand_eval):

1. **Ad Unit override** — ``pipeline_model_config[node_key]`` on the VideoAdUnit
2. **PipelineSettings node default** — per-node default in the singleton settings
3. **PipelineSettings global default** — app-level fallback for all nodes
4. **Language primary model** — the language's configured LLM (ultimate fallback)

**Writer node** (different chain — prioritizes language over app settings):

1. **Ad Unit override** — ``pipeline_model_config["writer"]``
2. **Ad Unit LLM override** — ``effective_llm_model`` FK on the ad unit
3. **Language primary model** — the language's configured LLM
4. **PipelineSettings global default** — app-level fallback

The writer node defaults to the language's primary model because it produces the target-language content and needs a model capable in that language.

Node Keys
---------

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Node Key
     - Pipeline Node
     - Role
   * - ``concept``
     - Concept Analyst
     - Extracts themes from origin script
   * - ``culture``
     - Cultural Researcher
     - Produces cultural brief for target market
   * - ``writer``
     - Script Writer
     - Adapts script for target audience
   * - ``format_gate``
     - Format Evaluator
     - Checks language compliance
   * - ``culture_gate``
     - Cultural Evaluator
     - Validates cultural sensitivity
   * - ``concept_gate``
     - Concept Evaluator
     - Verifies concept preservation
   * - ``brand_gate``
     - Brand Evaluator
     - Checks brand consistency

Setting Overrides at the Ad Unit Level
--------------------------------------

Each VideoAdUnit has a ``pipeline_model_config`` JSONField that maps node keys to LLM model primary keys:

.. code-block:: json

   {
     "concept": 2,
     "culture": 2,
     "writer": 5,
     "format_gate": 2,
     "culture_gate": 2,
     "concept_gate": 2,
     "brand_gate": 2
   }

To set overrides:

1. Navigate to the **Video Ad Unit** in the admin
2. Edit the **Pipeline Model Config** JSON field
3. Use the primary key of the desired ``LLMModel`` for each node
4. Save — the override applies to this ad unit's next pipeline run

Only include nodes you want to override. Omitted nodes fall through to PipelineSettings defaults.

Setting Defaults via PipelineSettings
--------------------------------------

PipelineSettings provides app-level defaults that apply to all adaptations unless overridden per-ad-unit:

1. Navigate to **Core > Pipeline Settings**
2. Select the LLM model for each node
3. Set the **Global Default Model** as the fallback for any unconfigured node
4. Save

See :doc:`pipeline-settings` for the full PipelineSettings guide.

Practical Examples
------------------

**Quality-focused configuration** — use a larger model for evaluation nodes:

.. code-block:: json

   {
     "concept": 3,
     "culture": 3,
     "writer": 5,
     "format_gate": 3,
     "culture_gate": 3,
     "concept_gate": 3,
     "brand_gate": 3
   }

Where model 3 is Qwen2.5-7B (higher quality) and model 5 is a language-specialized model for writing.

**Speed-focused configuration** — use a smaller model everywhere:

.. code-block:: json

   {
     "concept": 1,
     "culture": 1,
     "writer": 1
   }

Where model 1 is Qwen2.5-3B (faster). Evaluation nodes fall through to PipelineSettings defaults.

**Language-specialized writing** — override only the writer for a market with specific language requirements:

.. code-block:: json

   {
     "writer": 7
   }

Where model 7 is a model with strong capabilities in the target language. All other nodes use PipelineSettings defaults.

How Resolution Works
--------------------

The ``resolve_pipeline_models()`` function in ``src/cw/lib/pipeline/state.py`` executes the resolution chain:

1. Loads the ``PipelineSettings`` singleton
2. Gets the ad unit's ``pipeline_model_config`` overrides
3. For each node key, walks the fallback chain until a model is found
4. Returns a dictionary mapping node keys to ``{"model_id": str, "load_in_4bit": bool}``

Only active models (``is_active=True``) are used. If a referenced model has been deactivated, the resolution falls through to the next level.
