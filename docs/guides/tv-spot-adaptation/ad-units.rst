Origin & Adaptation Ad Units
============================

This guide explains the ad unit model, the origin-to-adaptation chain, and how to configure adaptations for target markets.

Ad Unit Model
-------------

**AdUnit** is a polymorphic base class using Django multi-table inheritance. Currently, the only concrete type is **VideoAdUnit** (with ``AUDIO`` and ``PRINT`` planned for the future).

Every ad unit belongs to a Campaign and is classified as either:

- **Origin** — the source creative, typically in the campaign's home market
- **Adaptation** — a culturally-adapted version targeting a specific market

.. mermaid::

   graph LR
       Origin["Origin VideoAdUnit<br/>(US-EN-001)"]
       A1["Adaptation<br/>(DE-DE-001)"]
       A2["Adaptation<br/>(JP-JA-001)"]
       A3["Adaptation<br/>(BR-PT-001)"]
       Origin --> A1
       Origin --> A2
       Origin --> A3

The ``source_ad_unit`` FK links each adaptation back to its origin, creating a traceable adaptation chain within a single campaign.

Creating an Origin Ad Unit
--------------------------

An origin ad unit represents the source creative:

1. Navigate to **TV Spots > Video Ad Units > Add Video Ad Unit**
2. Select the **Campaign**
3. Set **Origin or Adaptation** to ``Origin``
4. Enter a **Code** (e.g., ``US-EN-001``)
5. Optionally set **Duration** and **Visual Style Prompt**
6. Save — the status defaults to ``completed`` for origins

Add script rows inline using the **Ad Unit Script Rows** section at the bottom of the form:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - **Order Index**
     - Row position (0-based)
   * - **Shot Number**
     - Shot or scene number (e.g., ``01``, ``02``)
   * - **Timecode**
     - Timecode in ``HH:MM:SS:FF`` or ``HH:MM:SS.mmm`` format
   * - **Visual Text**
     - Visual description — shot composition, action, talent direction, supers
   * - **Audio Text**
     - Audio content — voiceover, music, sound effects, dialogue

Creating an Adaptation Ad Unit
------------------------------

An adaptation targets a specific market and can be processed by the multi-agent pipeline:

1. Navigate to **TV Spots > Video Ad Units > Add Video Ad Unit**
2. Select the same **Campaign** as the origin
3. Set **Origin or Adaptation** to ``Adaptation``
4. Set **Source Ad Unit** to the origin ad unit
5. Configure the target market:

   - **Region** — geographic region (e.g., DACH, LATAM, EU-WEST)
   - **Country** — target country (e.g., Germany, Japan)
   - **Language** — target language (e.g., ``de-DE``, ``ja-JP``)
   - **Persona** — optional audience persona for targeting
   - **Brand** — optional market-specific brand override (e.g., Walkers instead of Lay's)

6. Enable **Use Pipeline** to run the multi-agent adaptation pipeline
7. Save — the pipeline task is automatically queued

Pipeline Status Lifecycle
-------------------------

When the pipeline runs, the ad unit's status progresses through these stages:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Status
     - Display Name
     - Description
   * - ``pending``
     - Pending
     - Task not yet started
   * - ``processing``
     - Processing
     - Task dispatched to worker
   * - ``concept_analysis``
     - Analyzing Concept
     - Extracting themes from origin script
   * - ``cultural_analysis``
     - Researching Culture
     - Producing cultural brief for target market
   * - ``writing``
     - Writing Script
     - Adapting script for target audience
   * - ``format_evaluation``
     - Evaluating Format
     - Checking language compliance
   * - ``cultural_evaluation``
     - Evaluating Culture
     - Validating cultural sensitivity
   * - ``concept_evaluation``
     - Evaluating Concept
     - Verifying concept preservation
   * - ``brand_evaluation``
     - Evaluating Brand
     - Checking brand consistency
   * - ``revising``
     - Revising Script
     - Rewriting after evaluation failure
   * - ``completed``
     - Completed
     - All evaluations passed
   * - ``failed``
     - Failed
     - Pipeline error or max retries exhausted

See :doc:`/concepts/adaptation-pipeline` for the full pipeline architecture.

Per-Node Model Configuration
-----------------------------

Each pipeline node can use a different LLM model. The resolution chain for each node:

1. **Ad Unit override** — ``pipeline_model_config`` JSONField on the ad unit
2. **PipelineSettings node default** — per-node default in the singleton settings
3. **PipelineSettings global default** — fallback for all nodes
4. **Language primary model** — the language's configured LLM

The ``pipeline_model_config`` field accepts a JSON object mapping node keys to LLM model PKs:

.. code-block:: json

   {
     "concept": 2,
     "culture": 2,
     "writer": 5,
     "format_eval": 2,
     "cultural_eval": 2,
     "concept_eval": 2,
     "brand_eval": 2
   }

The **writer** node defaults to the language's primary model instead of the global default, since it produces the target-language content.

Brand Override
--------------

Adaptations can override the campaign's brand to handle market-specific trade names:

.. code-block:: text

   Campaign brand: Lay's
   UK adaptation brand: Walkers
   India adaptation brand: Lay's India

The ``effective_brand`` property resolves the brand: ad unit override first, then campaign default. The brand evaluation node uses whichever brand is resolved.

Pipeline Output
---------------

After the pipeline completes, the ad unit stores:

- **Concept Brief** — structured analysis of the origin script's themes, emotions, and narrative
- **Cultural Brief** — research on the target market's communication style, values, and taboos
- **Evaluation History** — results from each evaluation gate (pass/fail, reasons, revision counts)
- **Pipeline Metadata** — timing information and model IDs used
- **Script Rows** — the adapted script as ``AdUnitScriptRow`` records

These fields are visible on the ad unit's detail page in the admin and are used for auditing adaptation quality.

Visual Style Prompt
-------------------

The **Visual Style Prompt** field on ``VideoAdUnit`` provides a common style prefix applied to all storyboard image prompts. This ensures visual consistency across frames:

.. code-block:: text

   warm cinematic lighting, 35mm film grain, shallow depth of field

When generating storyboards, this prefix is prepended to each script row's visual description before image generation. See :doc:`storyboards` for details.
