Database Schema
===============

Entity-relationship diagram for the Generative Creative Lab Django models.
Please review the API documentation for :doc:`cw.diffusion <api/diffusion>` 
and :doc:`cw.tvspots <api/tvspots>` for details regarding these models.

.. mermaid::

   ---
   title: Database Schema
   config:
     layout: elk
   ---
   erDiagram
       classDef appDiffusionClass fill:#440,color:#fff;
       classDef appTvSpotClass fill:#036,color:#fff;

       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       %% DIFFUSION APP (cw.diffusion)
       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       direction TB
         DiffusionModel:::appDiffusionClass
         LoraModel:::appDiffusionClass
         Prompt:::appDiffusionClass
         DiffusionJob:::appDiffusionClass

       DiffusionModel ||--o{ DiffusionJob : "generates"
       LoraModel ||--o{ DiffusionJob : "applies to"
       Prompt ||--o{ DiffusionJob : "uses"

       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       %% TV SPOTS APP (cw.tvspots)
       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

       direction TB
         AdaptationMarket:::appTvSpotClass
         TvSpot:::appTvSpotClass
         TvSpotVersion:::appTvSpotClass
         TvSpotScriptRow:::appTvSpotClass
         AdaptationJob:::appTvSpotClass
         StoryboardJob:::appTvSpotClass
         StoryboardImage:::appTvSpotClass

       TvSpot ||--o{ TvSpotVersion : "has versions"
       TvSpot ||--o{ AdaptationJob : "requests"
       AdaptationMarket ||--o{ TvSpotVersion : "target for"
       AdaptationMarket ||--o{ AdaptationJob : "target for"
       TvSpotVersion ||--o{ TvSpotScriptRow : "contains"
       TvSpotVersion ||--o{ StoryboardJob : "generates"
       TvSpotVersion ||--o{ AdaptationJob : "origin for"
       AdaptationJob ||--o| TvSpotVersion : "creates"
       StoryboardJob ||--o{ StoryboardImage : "produces"
       TvSpotScriptRow ||--o{ StoryboardImage : "source for"

       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       %% CROSS-APP REFERENCES
       %% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       DiffusionModel ||--o{ StoryboardJob : "renders"
       LoraModel ||--o{ StoryboardJob : "styles"
       DiffusionJob ||--o{ StoryboardImage : "generates"

----

Diffusion App
-------------

Core models for image generation: model configuration, LoRA adapters, prompts, and jobs.

**DiffusionModel**
   Configuration for a diffusion model (Flux, SDXL, SD1.5, etc.). Stores inference
   parameters like steps, guidance scale, resolution, and scheduler. Models are
   imported from ``data/presets.json`` via the ``import_presets`` management command.

**LoraModel**
   Low-Rank Adaptation models that modify base model behavior. Can be auto-downloaded
   from CivitAI using AIR URNs. Filtered by ``base_architecture`` to ensure compatibility
   with the selected diffusion model.

**Prompt**
   User prompts with optional AI enhancement. Supports multiple enhancement methods
   (rule-based, local HuggingFace model, or LLM API) and style presets.

**DiffusionJob**
   Tracks image generation tasks processed by Celery workers. Links a prompt to a
   model (and optional LoRA), stores parameter overrides, and tracks status/results.

----

TV Spots App
------------

Models for TV commercial workflow: spots, versions, scripts, and storyboard generation.

**AdaptationMarket**
   Target markets for TV spot localization with structured cultural/regulatory rules.
   Rules are stored as JSON and rendered as markdown for LLM consumption.
   See :doc:`/research/AdaptationProfiles` for the full market profiles framework.

**TvSpot**
   Project-level metadata for a TV commercial (client, brand, title, runtime).
   Created via JSON import. Each spot has one origin version and zero or more
   market adaptations.

**TvSpotVersion**
   A specific version of a spot - either the original ("origin") or a market
   adaptation. Each version has its own script rows and can have multiple
   storyboard generation runs.

**TvSpotScriptRow**
   A single row in the two-column A/V script format. Left column (visual_text)
   contains shots, graphics, and supers. Right column (audio_text) contains
   VO, dialogue, SFX, and music cues.

**AdaptationJob**
   Tracks adaptation requests from origin to target market. Created when user
   requests an adaptation, updated by Celery task. Links to result_version on
   completion. Enables status visibility in admin while task is processing.

**StoryboardJob**
   Coordinates storyboard generation for a TvSpotVersion. Creates one DiffusionJob
   per script row (multiplied by ``images_per_row``). Tracks overall progress.

**StoryboardImage**
   Junction table linking StoryboardJob, TvSpotScriptRow, and DiffusionJob.
   Allows multiple images per row and multiple storyboard runs per version.

----

Cross-App References
--------------------

The ``tvspots`` app references models from the ``diffusion`` app:

- ``StoryboardJob.diffusion_model`` → ``DiffusionModel``
- ``StoryboardJob.lora_model`` → ``LoraModel``
- ``StoryboardImage.diffusion_job`` → ``DiffusionJob``

This creates a clean separation where ``diffusion`` handles image generation
and ``tvspots`` handles TV commercial workflow orchestration.

----

Cascade Behavior
----------------

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Relationship
     - On Delete
     - Rationale
   * - DiffusionJob → DiffusionModel
     - PROTECT
     - Preserve job history
   * - DiffusionJob → LoraModel
     - SET_NULL
     - Allow LoRA deletion
   * - DiffusionJob → Prompt
     - PROTECT
     - Preserve job history
   * - TvSpotVersion → TvSpot
     - CASCADE
     - Delete versions with spot
   * - TvSpotVersion → AdaptationMarket
     - PROTECT
     - Preserve market reference
   * - TvSpotScriptRow → TvSpotVersion
     - CASCADE
     - Delete rows with version
   * - AdaptationJob → TvSpot
     - CASCADE
     - Delete jobs with spot
   * - AdaptationJob → TvSpotVersion (origin)
     - CASCADE
     - Delete jobs with origin version
   * - AdaptationJob → AdaptationMarket
     - PROTECT
     - Preserve market reference
   * - AdaptationJob → TvSpotVersion (result)
     - SET_NULL
     - Allow orphan jobs if version deleted
   * - StoryboardJob → TvSpotVersion
     - CASCADE
     - Delete jobs with version
   * - StoryboardImage → StoryboardJob
     - CASCADE
     - Delete images with job
   * - StoryboardImage → DiffusionJob
     - CASCADE
     - Delete links with job
