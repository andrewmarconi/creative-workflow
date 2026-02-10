Adaptation Pipeline
===================

This page explains the multi-agent cultural adaptation system: the LangGraph graph, the 7 pipeline nodes, evaluation gates with retry logic, model resolution, and output artifacts.

Overview
--------

The adaptation pipeline takes an origin TV spot script and produces a culturally adapted version for a target market. It runs as a **LangGraph state machine** with 7 nodes — 3 generation nodes and 4 evaluation gates — connected by conditional edges that route failures back to the writer for revision.

The pipeline uses **structured generation** via the `Outlines <https://github.com/dottxt-ai/outlines>`_ library, constraining LLM output to Pydantic schemas so every node produces validated, parseable JSON.

Graph Structure
---------------

.. mermaid::

   graph TD
       START([Start]) --> concept[Concept Analyst]
       concept --> culture[Cultural Researcher]
       culture --> writer[Writer]
       writer --> format_eval[Format Evaluator]

       format_eval -->|pass| cultural_eval[Cultural Evaluator]
       format_eval -->|"fail (retries left)"| writer
       format_eval -->|"fail (exhausted)"| FAIL([Failed])

       cultural_eval -->|pass| concept_eval[Concept Evaluator]
       cultural_eval -->|"fail (retries left)"| writer
       cultural_eval -->|"fail (exhausted)"| FAIL

       concept_eval -->|pass| brand_eval[Brand Evaluator]
       concept_eval -->|"fail (retries left)"| writer
       concept_eval -->|"fail (exhausted)"| FAIL

       brand_eval -->|pass| END([Completed])
       brand_eval -->|"fail (retries left)"| writer
       brand_eval -->|"fail (exhausted)"| FAIL

The first three nodes run in sequence. After the writer produces an adapted script, four evaluation gates run in series. If any gate fails and retries remain, the pipeline loops back to the writer with feedback. If retries are exhausted, the pipeline terminates with a failure status.

Pipeline Nodes
--------------

Concept Analyst
^^^^^^^^^^^^^^^

**Status**: ``concept_analysis`` | **Schema**: ``ConceptBrief`` | **Prompt**: ``concept-extraction``

Analyzes the origin script and extracts:

- **Core message** — the primary selling proposition
- **Emotional beats** — key emotional moments in the narrative
- **Narrative structure** — story arc (setup, conflict, resolution)
- **Themes** — universal and culture-specific themes
- **Cultural assumptions** — embedded assumptions in the original
- **Must-preserve vs. can-adapt** — what's sacred and what's flexible
- **Brand voice** — tone, style, personality

The concept brief is saved to the VideoAdUnit and passed to subsequent nodes as context.

Cultural Researcher
^^^^^^^^^^^^^^^^^^^

**Status**: ``cultural_analysis`` | **Schema**: ``CulturalBrief`` | **Prompt**: ``cultural-research``

Investigates the target market using the concept brief, hierarchical audience insights, and the origin script. Produces:

- **Market context** — cultural summary of the target market
- **Substitutions** — specific cultural references to replace, with rationale
- **Tone adjustments** — how to adapt voice and style
- **Pitfalls** — cultural sensitivities to avoid
- **Opportunities** — cultural hooks to leverage
- **Regulatory notes** — compliance considerations

The cultural brief is saved to the VideoAdUnit.

Writer
^^^^^^

**Status**: ``writing`` or ``revising`` | **Schema**: ``AdaptationOutput`` | **Prompt**: ``adaptation``

Generates (or revises) the adapted script. The writer receives:

- The concept and cultural briefs from the previous nodes
- The origin script and target market context
- Revision feedback from whichever evaluator failed (if revising)

The system prompt enforces a critical language rule: all visual descriptions and stage directions must remain in English. Only voiceover and on-screen text (supers, titles) are written in the target language, with English translations in parentheses.

After 2 total failed revision attempts across all gates, the writer **switches to an alternative LLM model** (if one is configured for the target language) to break out of revision loops.

Format Evaluator
^^^^^^^^^^^^^^^^

**Status**: ``format_evaluation`` | **Schema**: ``EvaluationResult`` | **Prompt**: ``eval-format``

Verifies language compliance:

- Visual descriptions are in English
- Voiceover and supers are in the target language
- English translations are provided in parentheses
- Row structure matches the expected format

Cultural Evaluator
^^^^^^^^^^^^^^^^^^

**Status**: ``cultural_evaluation`` | **Schema**: ``EvaluationResult`` | **Prompt**: ``eval-cultural``

Validates cultural appropriateness by checking the adapted script against the cultural brief and target market insights.

Concept Evaluator
^^^^^^^^^^^^^^^^^

**Status**: ``concept_evaluation`` | **Schema**: ``EvaluationResult`` | **Prompt**: ``eval-concept``

Ensures the adapted script preserves the original campaign intent by comparing it against the concept brief.

Brand Evaluator
^^^^^^^^^^^^^^^

**Status**: ``brand_evaluation`` | **Schema**: ``EvaluationResult`` | **Prompt**: ``eval-brand``

Checks brand consistency — voice, values, visual identity, and messaging guidelines — using the brand's guidelines from the ``Brand`` model.

Evaluation Gates
----------------

Each evaluation node produces an ``EvaluationResult`` with:

- **passed** — boolean pass/fail
- **score** — quality score from 0.0 to 1.0
- **issues** — list of issues with severity (critical/major/minor), description, location, and suggested fix
- **summary** — brief evaluation summary

The routing logic after each gate:

1. **Pass** (feedback is ``None``) — advance to the next gate
2. **Fail with retries remaining** — route back to the writer with feedback
3. **Fail with retries exhausted** — terminate the pipeline

Each gate allows a maximum of **3 retries** (configurable via ``MAX_*_RETRIES`` constants). Revision counts are tracked separately per gate (``format_revision_count``, ``cultural_revision_count``, etc.), and each evaluation result is appended to the VideoAdUnit's ``evaluation_history`` JSON array.

When the writer receives revision feedback, it clears all feedback fields before generating a new draft, ensuring the revised script is re-evaluated through all subsequent gates.

Model Resolution
----------------

Each pipeline node can use a different LLM. The model for a given node is resolved through a fallback chain:

**Non-writer nodes** (concept, culture, format gate, cultural gate, concept gate, brand gate):

1. ``VideoAdUnit.pipeline_model_config[node_key]`` — per-adaptation override (JSON field)
2. ``PipelineSettings.<node_key>_default_model`` — app-level node default
3. ``PipelineSettings.global_default_model`` — app-level fallback
4. ``Language.primary_model`` — ultimate fallback

**Writer node**:

1. ``VideoAdUnit.pipeline_model_config["writer"]`` — per-adaptation override
2. ``VideoAdUnit.llm_model`` — legacy FK override
3. ``Language.primary_model`` — language default
4. ``PipelineSettings.global_default_model`` — app-level fallback

The writer has a different chain because it benefits from using a model tuned for the target language, while evaluation gates are less language-sensitive.

``PipelineSettings`` is a singleton model (accessed via ``PipelineSettings.get_instance()``) that provides app-level defaults for each node. Administrators can configure different models for different tasks — for example, a smaller model for evaluation gates and a larger model for writing.

PipelineModelLoader
-------------------

The ``PipelineModelLoader`` is a **singleton** that manages the LLM used by pipeline nodes:

- **Lazy loading** — the model loads on the first call to ``get_generator()``
- **Schema-flexible** — the same loaded model serves generators for different Pydantic schemas (``ConceptBrief``, ``CulturalBrief``, ``EvaluationResult``, etc.)
- **Model switching** — the writer node can call ``switch_model()`` to swap to an alternative LLM after repeated failures
- **4-bit quantization** — supported on CUDA via BitsAndBytes (``nf4`` quant type with double quantization)

The singleton is shared across all nodes in a single pipeline execution. When the Celery worker starts a new adaptation task, the loader either reuses the existing model (if it matches) or loads a new one.

The loader wraps Outlines generators with retry logic for numerical stability errors (NaN, inf values in probability tensors) and FSM state errors (schema constraint violations). On FSM errors, the retry reduces the token limit by 50% to give the model more flexibility.

Output Artifacts
----------------

A completed pipeline run produces four artifacts, all persisted to the VideoAdUnit:

**Concept Brief** (``concept_brief`` JSON field)
   Structured analysis of the origin script: core message, emotional beats, narrative structure, themes, cultural assumptions, and brand voice.

**Cultural Brief** (``cultural_brief`` JSON field)
   Target market research: market context, cultural substitutions, tone adjustments, pitfalls, opportunities, and regulatory notes.

**Evaluation History** (``evaluation_history`` JSON array)
   Chronological record of every evaluation result — type, pass/fail, score, issues, and summary. Includes both passing and failing evaluations, providing a full audit trail.

**Adapted Script Rows** (``AdUnitScriptRow`` records)
   The final adapted script, saved as individual rows linked to the VideoAdUnit. Each row has a shot number, timecode, visual description (English), and audio (target language with English translations).

Pipeline metadata (revision counts, final model ID, final status) is also saved for diagnostic purposes.
