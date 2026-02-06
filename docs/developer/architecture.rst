System Architecture
===================

This guide provides a comprehensive overview of Generative Creative Lab's architecture,
including the process model, data flow, and design patterns used throughout the system.

.. contents:: Table of Contents
   :local:
   :depth: 2

System Overview
---------------

Generative Creative Lab is a Django + Celery application for multi-model diffusion image
generation. The system is designed around asynchronous task processing to handle
GPU-intensive operations without blocking the web interface.

.. mermaid::

   flowchart TB
       subgraph cw["Generative Creative Lab"]
           admin["Django Admin UI<br/>:8000"]
           broker["Celery Broker<br/>(Valkey)"]
           workers["Celery Workers<br/>(GPU tasks)"]
           db["PostgreSQL<br/>Database"]
           models["HuggingFace<br/>Models + LoRAs"]
           images["Generated Images<br/>(media/diffusion)"]
       end

       admin --> broker
       broker --> workers
       admin --> db
       workers --> models
       workers --> images

Key Components
~~~~~~~~~~~~~~

**Django Application** (``cw/``)
    The main application providing the admin interface, ORM models, and task
    orchestration. Uses Django Unfold for the admin UI.

**Celery Workers**
    Asynchronous task processors that handle GPU-intensive operations like
    image generation and prompt enhancement.

**Valkey/Redis Broker**
    Message broker for Celery task queues. Valkey is a Redis-compatible
    in-memory data store.

**PostgreSQL Database**
    Stores all application data including models, LoRAs, prompts, and job status.

**HuggingFace Models**
    Diffusion models loaded from HuggingFace Hub or local files, cached in
    memory for fast subsequent generations.

Process Model
-------------

Generative Creative Lab runs four concurrent processes, defined in the ``Procfile``
and launched via ``uv run honcho start``:

.. mermaid::

   flowchart LR
       subgraph docker["docker"]
           pg["PostgreSQL :5435"]
           valkey["Valkey :6379"]
           subgraph observability["Observability"]
               loki["Loki :3100"]
               alloy["Alloy"]
               grafana["Grafana :3000"]
           end
       end

       subgraph django["django"]
           server["Django Dev Server :8000"]
       end

       subgraph worker["worker"]
           gen["Image Generation<br/>(default queue)"]
       end

       subgraph enhancement["enhancement"]
           llm["Prompt Enhancement<br/>(enhancement queue)"]
       end

       server --> valkey
       valkey --> gen
       valkey --> llm
       server --> pg
       alloy --> loki
       grafana --> loki

Procfile Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    docker:      docker compose up
    django:      uv run manage.py runserver
    worker:      PYTHONPATH=src uv run celery -A cw worker -Q default --pool=solo
    enhancement: PYTHONPATH=src uv run celery -A cw worker -Q enhancement --pool=solo

Queue Structure
~~~~~~~~~~~~~~~

Two separate Celery queues isolate different workloads:

**default queue**
    Handles GPU-intensive image generation tasks. Tasks include:

    - ``generate_images_task`` - Main image generation
    - Model loading and LoRA application

**enhancement queue**
    Handles prompt enhancement via local LLM. Tasks include:

    - ``enhance_prompt_task`` - Prompt expansion using Qwen model

Why Solo Pool?
~~~~~~~~~~~~~~

Both workers use Celery's ``solo`` pool (single-threaded execution) because:

1. **GPU Context Safety**: MPS (Apple Silicon) and CUDA contexts are not
   fork-safe. Using ``prefork`` pool would cause GPU memory corruption.

2. **Model Memory**: Each diffusion model requires significant GPU memory.
   Running multiple concurrent tasks would exceed available memory.

3. **Predictable Execution**: Single-threaded execution ensures consistent
   behavior and easier debugging.

Data Flow
---------

Image Generation Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~

The typical flow from user input to generated image:

.. mermaid::

   flowchart LR
       A["Create Prompt<br/>(Admin)"] --> B["Create Job<br/>(Admin)"]
       B --> C["Celery Task<br/>Queued"]
       C --> D["Model<br/>Generate"]
       D --> E["Save to<br/>Media"]
       E --> F["Status<br/>Updated"]
       F --> G["View in<br/>Admin"]

**Step-by-step:**

1. **Create Prompt**: User creates a ``Prompt`` record via Django admin with
   the text description and optional enhancement settings.

2. **Create Job**: User creates a ``DiffusionJob`` linked to the prompt,
   selecting model, LoRA, dimensions, and generation parameters.

3. **Auto-Queue**: The admin ``save_model()`` hook automatically queues the
   job to Celery when status is "pending".

4. **Task Execution**: Worker picks up the task, loads the model (from cache
   if available), optionally applies LoRA, and generates images.

5. **Save Results**: Generated images are saved to ``media/diffusion/`` with
   metadata embedded as PNG chunks.

6. **Status Update**: Job status is updated to "completed" with result count.

Model Loading and Caching
~~~~~~~~~~~~~~~~~~~~~~~~~

Models are cached in memory to avoid repeated loading:

.. code-block:: python

    # Module-level cache in tasks.py
    _model_cache: Dict[str, BaseModel] = {}

    def get_or_load_model(model_slug: str) -> BaseModel:
        if model_slug not in _model_cache:
            # Clear previous model to free memory
            _model_cache.clear()
            torch.mps.empty_cache()  # or torch.cuda.empty_cache()

            # Load new model
            _model_cache[model_slug] = ModelFactory.create_model(...)

        return _model_cache[model_slug]

**Key behaviors:**

- Only one model is kept in memory at a time
- Switching models clears the cache and GPU memory
- LoRAs are loaded/unloaded per-job, not cached

LoRA Loading Flow
~~~~~~~~~~~~~~~~~

.. mermaid::

   flowchart TD
       A{"Job has<br/>LoRA set?"} -->|No| B["Skip LoRA<br/>loading"]
       A -->|Yes| C{"File<br/>exists?"}
       C -->|Yes| D["Load LoRA<br/>weights"]
       C -->|No| E["Download from<br/>CivitAI"]
       E --> F["Extract<br/>metadata"]
       F --> G["Update DB<br/>record"]
       G --> D
       D --> H["Apply to<br/>pipeline"]

LoRAs can be auto-downloaded from CivitAI using AIR URNs.

Model Architecture
------------------

Generative Creative Lab uses the **Template Method Pattern** for diffusion model
implementations, reducing code duplication while allowing model-specific
customization.

Class Hierarchy
~~~~~~~~~~~~~~~

.. mermaid::

   classDiagram
       class BaseModel {
           <<abstract>>
           +load_pipeline()
           +generate()
           #_create_pipeline()*
           #_build_prompts()
           #_build_pipeline_kwargs()
           #_apply_device_optimizations()
       }

       class CompelPromptMixin {
           +_build_prompts()
       }

       class ZImageTurboModel {
           #_create_pipeline()
       }

       class FluxModel {
           #_create_pipeline()
       }

       class SDXLModel {
           #_create_pipeline()
       }

       BaseModel <|-- ZImageTurboModel
       BaseModel <|-- FluxModel
       BaseModel <|-- SDXLModel
       CompelPromptMixin <|-- SDXLModel

Mixins
~~~~~~

Shared behaviors are implemented as mixins:

**CompelPromptMixin**
    Handles long prompts (>77 tokens) and prompt weighting syntax
    ``(word:1.3)`` for CLIP-based models (SDXL, SD15).

**CLIPTokenLimitMixin** (Legacy)
    Simple 77-token truncation. Deprecated in favor of CompelPromptMixin.

**DebugLoggingMixin**
    Adds debug print statements when enabled via config.

Example Implementation
~~~~~~~~~~~~~~~~~~~~~~

A minimal model implementation requires only ~20 lines:

.. code-block:: python

    from diffusers import YourPipeline
    from .base import BaseModel

    class YourModel(BaseModel):
        def _create_pipeline(self):
            return YourPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
            )

See :doc:`/user/guides/adding-models` for the complete guide.

Configuration Flags
~~~~~~~~~~~~~~~~~~~

Model behavior can be customized via flags in ``presets.json``:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Flag
     - Description
   * - ``force_default_guidance``
     - Ignore guidance_scale parameter (for Turbo models)
   * - ``enable_debug_logging``
     - Enable debug print statements
   * - ``use_sequential_cpu_offload``
     - Use sequential vs model CPU offload (CUDA)
   * - ``max_sequence_length``
     - Context length for Flux models
   * - ``load_in_8bit``
     - Enable 8-bit quantization

Database Schema
---------------

The platform uses three Django apps with distinct responsibilities. This section provides
detailed entity-relationship diagrams and field-level documentation for each app.

Diffusion App (cw.diffusion)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Core models for image generation: model configuration, LoRA adapters, prompts, and jobs.

.. mermaid::

   erDiagram
       DiffusionModel {
           bigint id PK
           varchar label
           varchar slug UK
           varchar base_architecture
           varchar path
           varchar pipeline
           int steps
           float guidance_scale
           int default_width
           int default_height
           int max_pixels
           varchar scheduler
           varchar dtype
           bool supports_negative_prompt
           bool force_default_guidance
           int max_sequence_length
           int token_window
           int vram_usage
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       LoraModel {
           bigint id PK
           varchar label
           varchar path
           varchar air
           varchar base_architecture
           text prompt_suffix
           text negative_prompt_suffix
           float default_strength
           float guidance_scale
           int clip_skip
           text notes
           varchar theme
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       Prompt {
           bigint id PK
           text source_prompt
           text enhanced_prompt
           text negative_prompt
           varchar enhancement_style
           varchar enhancement_method
           float creativity
           timestamp created_at
           timestamp updated_at
       }

       DiffusionJob {
           bigint id PK
           bigint diffusion_model_id FK
           bigint lora_model_id FK
           bigint prompt_id FK
           varchar identifier
           int width
           int height
           int steps
           float guidance_scale
           float lora_strength
           bigint seed
           varchar scheduler
           int num_images
           varchar status
           varchar rq_job_id
           array result_images
           json generation_metadata
           text error_message
           timestamp created_at
           timestamp started_at
           timestamp completed_at
       }

       DiffusionModel ||--o{ DiffusionJob : "generates"
       LoraModel ||--o{ DiffusionJob : "applies to"
       Prompt ||--o{ DiffusionJob : "uses"

**DiffusionModel**
   Configuration for a diffusion model (Flux, SDXL, SD1.5, etc.). Models are imported from
   ``data/presets.json`` via the ``import_presets`` management command.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``label``
        - varchar(255)
        - Display name for the model
      * - ``slug``
        - varchar(100)
        - Unique identifier (e.g., 'flux1_dev', 'sdxl_turbo')
      * - ``base_architecture``
        - varchar(20)
        - Architecture type: sdxl, sd15, flux1, qwen, zimage
      * - ``path``
        - varchar(500)
        - HuggingFace model ID or local .safetensors path
      * - ``pipeline``
        - varchar(100)
        - Pipeline class name (e.g., 'FluxPipeline', 'StableDiffusionXLPipeline')
      * - ``steps``
        - int
        - Default number of inference steps (1-200)
      * - ``guidance_scale``
        - float
        - Default CFG value (0.0-20.0)
      * - ``default_width``
        - int
        - Default image width in pixels (256-4096)
      * - ``default_height``
        - int
        - Default image height in pixels (256-4096)
      * - ``max_pixels``
        - int
        - Maximum total pixels (width × height)
      * - ``scheduler``
        - varchar(100)
        - Default scheduler (e.g., 'FlowMatchEulerDiscreteScheduler')
      * - ``dtype``
        - varchar(50)
        - Data type: bfloat16, float16, float32, float8_e4m3fn
      * - ``supports_negative_prompt``
        - bool
        - Whether model accepts negative prompts
      * - ``force_default_guidance``
        - bool
        - Force model's default guidance_scale (for Turbo models)
      * - ``max_sequence_length``
        - int
        - Maximum sequence length for text encoder
      * - ``token_window``
        - int
        - Maximum tokens for prompt (77 for CLIP, 512 for T5)
      * - ``vram_usage``
        - int
        - Minimum VRAM required in MB
      * - ``is_active``
        - bool
        - Enable/disable model in admin

**LoraModel**
   Low-Rank Adaptation models that modify base model behavior. Can be auto-downloaded from
   CivitAI using AIR URNs.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``label``
        - varchar(255)
        - Display name for the LoRA
      * - ``path``
        - varchar(500)
        - Path to LoRA file or HF model ID
      * - ``air``
        - varchar(500)
        - AIR (AI Resource) URN identifier for CivitAI downloads
      * - ``base_architecture``
        - varchar(20)
        - Compatible architecture: sdxl, sd15, flux1, qwen, zimage
      * - ``prompt_suffix``
        - text
        - Trigger words and style description to append to prompts
      * - ``negative_prompt_suffix``
        - text
        - Terms to append to negative prompts
      * - ``default_strength``
        - float
        - Default LoRA strength/weight (0.0-2.0)
      * - ``guidance_scale``
        - float
        - Override guidance scale when using this LoRA
      * - ``clip_skip``
        - int
        - Number of CLIP layers to skip (1-12, typically 1-2 for anime)
      * - ``notes``
        - text
        - Internal notes (usage tips, characteristics, stats)
      * - ``theme``
        - varchar(100)
        - Theme for filtering: 'anime', 'photorealistic', 'fantasy'
      * - ``is_active``
        - bool
        - Enable/disable LoRA in admin

**Prompt**
   User prompts with optional AI enhancement. Supports multiple enhancement methods.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``source_prompt``
        - text
        - Original user-provided prompt
      * - ``enhanced_prompt``
        - text
        - AI-enhanced version of the prompt
      * - ``negative_prompt``
        - text
        - Negative prompt (things to avoid)
      * - ``enhancement_style``
        - varchar(50)
        - Style preset: auto, photography, artistic, realistic, cinematic, coloring-book
      * - ``enhancement_method``
        - varchar(50)
        - Method: none, rule-based, huggingface, llm
      * - ``creativity``
        - float
        - Creativity level for enhancement (0.0-1.0)

**DiffusionJob**
   Tracks image generation tasks processed by Celery workers. Links a prompt to a model
   (and optional LoRA), stores parameter overrides, and tracks status/results.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``diffusion_model``
        - FK
        - Model to use for generation (PROTECT on delete)
      * - ``lora_model``
        - FK
        - Optional LoRA to apply (SET_NULL on delete)
      * - ``prompt``
        - FK
        - Prompt to use for generation (PROTECT on delete)
      * - ``identifier``
        - varchar(100)
        - Optional identifier for file naming
      * - ``width``
        - int
        - Image width override (uses model default if not set)
      * - ``height``
        - int
        - Image height override (uses model default if not set)
      * - ``steps``
        - int
        - Steps override (uses model default if not set)
      * - ``guidance_scale``
        - float
        - Guidance scale override (uses model default if not set)
      * - ``lora_strength``
        - float
        - LoRA strength override (uses LoRA default if not set)
      * - ``seed``
        - bigint
        - Random seed for reproducibility (random if not set)
      * - ``scheduler``
        - varchar(100)
        - Scheduler override (uses model default if not set)
      * - ``num_images``
        - int
        - Number of images to generate (1-10)
      * - ``status``
        - varchar(20)
        - Job status: pending, queued, processing, completed, failed, cancelled
      * - ``rq_job_id``
        - varchar(255)
        - Celery task ID for tracking
      * - ``result_images``
        - array
        - List of generated image paths
      * - ``generation_metadata``
        - json
        - Complete generation settings used
      * - ``error_message``
        - text
        - Error message if job failed
      * - ``started_at``
        - timestamp
        - When job processing started
      * - ``completed_at``
        - timestamp
        - When job finished

TV Spots App (cw.tvspots)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Models for TV commercial workflow: spots, versions, scripts, adaptations, and storyboard generation.

.. mermaid::

   erDiagram
       AdaptationMarket {
           bigint id PK
           varchar name UK
           varchar code UK
           bigint default_language_id FK
           json rules
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       TvSpot {
           bigint id PK
           varchar client_name
           varchar brand_name
           varchar script_title
           int total_runtime_seconds
           varchar job_id UK
           text notes
           timestamp created_at
           timestamp updated_at
       }

       TvSpotVersion {
           bigint id PK
           bigint tv_spot_id FK
           varchar version_type
           bigint market_id FK
           varchar code
           varchar name
           varchar language
           text visual_style_prompt
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       TvSpotScriptRow {
           bigint id PK
           bigint tv_spot_version_id FK
           int order_index
           varchar shot_number
           varchar timecode_start
           decimal duration_seconds
           text visual_text
           text audio_text
       }

       AdaptationJob {
           bigint id PK
           bigint tv_spot_id FK
           bigint origin_version_id FK
           bigint target_market_id FK
           bigint language_id FK
           bigint llm_model_id FK
           bigint result_version_id FK
           varchar status
           varchar celery_task_id
           text error_message
           timestamp created_at
           timestamp started_at
           timestamp completed_at
       }

       StoryboardJob {
           bigint id PK
           bigint tv_spot_version_id FK
           bigint diffusion_model_id FK
           bigint lora_model_id FK
           int images_per_row
           varchar status
           text error_message
           timestamp created_at
           timestamp completed_at
       }

       StoryboardImage {
           bigint id PK
           bigint storyboard_job_id FK
           bigint script_row_id FK
           bigint diffusion_job_id FK
           int image_index
       }

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

**AdaptationMarket**
   Target markets for TV spot localization with structured cultural and regulatory rules.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``name``
        - varchar(100)
        - Market name (e.g., 'US Hispanic', 'Japanese')
      * - ``code``
        - varchar(20)
        - Short code (e.g., 'us-hispanic', 'jp')
      * - ``default_language``
        - FK
        - Default language for adaptations in this market
      * - ``rules``
        - json
        - Structured rules: list of {heading, points[]} for adaptation guidance
      * - ``is_active``
        - bool
        - Enable/disable market in admin

**TvSpot**
   Project-level metadata for a TV commercial. Created via JSON import.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``client_name``
        - varchar(255)
        - Client name
      * - ``brand_name``
        - varchar(255)
        - Brand name
      * - ``script_title``
        - varchar(255)
        - Title of the script
      * - ``total_runtime_seconds``
        - int
        - Total runtime in seconds (typically 15, 30, 60, 90)
      * - ``job_id``
        - varchar(100)
        - Internal project ID (e.g., 'ACME-2024-001')
      * - ``notes``
        - text
        - Additional notes

**TvSpotVersion**
   A version of a spot - either the origin or a market adaptation. Each version has its
   own script rows.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``tv_spot``
        - FK
        - Parent TV spot (CASCADE on delete)
      * - ``version_type``
        - varchar(20)
        - Type: 'origin' or 'adaptation'
      * - ``market``
        - FK
        - Target market for adaptation (null for origin, PROTECT on delete)
      * - ``code``
        - varchar(50)
        - Internal code (e.g., 'ORIGIN', 'US-HISP', 'JP')
      * - ``name``
        - varchar(255)
        - Human label (e.g., 'US Hispanic Adaptation')
      * - ``language``
        - varchar(50)
        - Primary language code (e.g., 'en-US', 'es-MX', 'ja')
      * - ``visual_style_prompt``
        - text
        - Common prompt prefix for storyboard generation consistency
      * - ``is_active``
        - bool
        - Enable/disable version

**TvSpotScriptRow**
   A single row in the two-column A/V script format. Left column (visual) and right
   column (audio) keep content aligned with timing metadata.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``tv_spot_version``
        - FK
        - Parent version (CASCADE on delete)
      * - ``order_index``
        - int
        - Row order in script (0-indexed)
      * - ``shot_number``
        - varchar(20)
        - Shot identifier (e.g., '01', '1A', 'MONT-01')
      * - ``timecode_start``
        - varchar(12)
        - Start timecode (e.g., '00:00:05:00' or '5.0')
      * - ``duration_seconds``
        - decimal
        - Row duration in seconds
      * - ``visual_text``
        - text
        - Left column: visuals, shots, graphics, supers, VFX, locations
      * - ``audio_text``
        - text
        - Right column: VO, dialogue, SFX, music cues, taglines

**AdaptationJob**
   Tracks adaptation requests from origin version to target market. Created when user
   requests an adaptation, updated by Celery task.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``tv_spot``
        - FK
        - Parent TV spot (CASCADE on delete)
      * - ``origin_version``
        - FK
        - Origin version to adapt from (CASCADE on delete)
      * - ``target_market``
        - FK
        - Target market for adaptation (PROTECT on delete)
      * - ``language``
        - FK
        - Override market's default language (PROTECT on delete)
      * - ``llm_model``
        - FK
        - Override language's primary model (PROTECT on delete)
      * - ``result_version``
        - FK
        - Created adaptation version (SET_NULL on delete)
      * - ``status``
        - varchar(20)
        - Job status: pending, processing, completed, failed
      * - ``celery_task_id``
        - varchar(255)
        - Celery task ID for tracking
      * - ``error_message``
        - text
        - Error message if job failed
      * - ``started_at``
        - timestamp
        - When job processing started
      * - ``completed_at``
        - timestamp
        - When job finished

**StoryboardJob**
   Coordinates storyboard generation for a TvSpotVersion. Creates one DiffusionJob per
   script row (multiplied by ``images_per_row``).

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``tv_spot_version``
        - FK
        - Version to generate storyboard for (CASCADE on delete)
      * - ``diffusion_model``
        - FK
        - Model to use for generation (PROTECT on delete)
      * - ``lora_model``
        - FK
        - Optional LoRA to apply (SET_NULL on delete)
      * - ``images_per_row``
        - int
        - Number of images to generate per script row
      * - ``status``
        - varchar(20)
        - Job status: pending, processing, completed, failed
      * - ``error_message``
        - text
        - Error message if job failed
      * - ``completed_at``
        - timestamp
        - When job finished

**StoryboardImage**
   Junction table linking StoryboardJob, TvSpotScriptRow, and DiffusionJob. Allows
   multiple images per row and multiple storyboard runs per version.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``storyboard_job``
        - FK
        - Parent storyboard job (CASCADE on delete)
      * - ``script_row``
        - FK
        - Source script row (CASCADE on delete)
      * - ``diffusion_job``
        - FK
        - Image generation job (CASCADE on delete)
      * - ``image_index``
        - int
        - Image sequence within the row (for multiple images per row)

Cross-App References
~~~~~~~~~~~~~~~~~~~~

The ``tvspots`` app references models from the ``diffusion`` app to integrate storyboard
generation with the core image generation system:

- ``StoryboardJob.diffusion_model`` → ``DiffusionModel``
- ``StoryboardJob.lora_model`` → ``LoraModel``
- ``StoryboardImage.diffusion_job`` → ``DiffusionJob``

This creates a clean separation where ``diffusion`` handles image generation and
``tvspots`` handles TV commercial workflow orchestration.

Observability
-------------

Logging
~~~~~~~

All components use structured JSON logging:

.. code-block:: text

    logs/
    ├── django.log           # Django server logs
    ├── celery.log           # Celery general logs
    ├── tasks.log            # Task execution logs
    ├── worker_default.log   # Image generation worker
    └── worker_enhancement.log  # Prompt enhancement worker

Grafana + Loki
~~~~~~~~~~~~~~

The Docker Compose stack includes observability tools:

- **Loki** (:3100) - Log aggregation backend
- **Alloy** - Unified observability collector shipping logs to Loki
- **Grafana** (:3000) - Web UI for log search and dashboards

Access Grafana at http://localhost:3000 (anonymous login enabled for dev).

See :doc:`/user/quickstart` for setup instructions.

Related Documentation
---------------------

- :doc:`/user/quickstart` - Getting started guide
- :doc:`/user/guides/adding-models` - Adding new diffusion models
- :doc:`api/lib` - API reference for cw.lib
- :doc:`api/diffusion` - API reference for cw.diffusion
