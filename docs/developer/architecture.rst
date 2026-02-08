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
           gen["All Tasks<br/>(default queue)"]
       end

       subgraph flower["flower"]
           mon["Task Monitor<br/>:5555"]
       end

       server --> valkey
       valkey --> gen
       server --> pg
       alloy --> loki
       grafana --> loki

Procfile Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

    docker:    docker compose up
    django:    uv run manage.py runserver
    worker:    PYTHONPATH=src uv run celery -A cw worker -Q default -E --loglevel=info --pool=solo
    flower:    PYTHONPATH=src uv run celery -A cw flower --port=5555

Queue Structure
~~~~~~~~~~~~~~~

A single Celery queue handles all workloads sequentially:

**default queue**
    All tasks run on a single queue to ensure sequential execution and prevent
    concurrent GPU model loading. Tasks include:

    - ``generate_images_task`` - Image generation
    - ``enhance_prompt_task`` - Prompt enhancement via local LLM
    - ``download_lora_task`` - LoRA downloading from CivitAI
    - ``create_adaptation_task`` - Multi-agent adaptation pipeline
    - ``generate_storyboard_task`` - Storyboard prompt generation and job creation

Why Solo Pool?
~~~~~~~~~~~~~~

The worker uses Celery's ``solo`` pool (single-threaded execution) because:

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

    def _load_model_instance(diffusion_model) -> BaseModel:
        slug = diffusion_model.slug
        if slug in _model_cache:
            return _model_cache[slug]

        # Clear previous model to free memory
        _model_cache.clear()
        torch.cuda.empty_cache()  # or torch.mps.empty_cache()

        # Load new model
        model_instance = ModelFactory.create_model(config, path)
        model_instance.load_pipeline(...)
        _model_cache[slug] = model_instance
        return model_instance

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

       class DebugLoggingMixin {
           +_debug_print()
       }

       class ZImageTurboModel {
           #_create_pipeline()
       }

       class FluxModel {
           #_create_pipeline()
       }

       class Flux2KleinModel {
           #_create_pipeline()
       }

       class QwenImageModel {
           #_create_pipeline()
       }

       class SDXLModel {
           #_create_pipeline()
       }

       class SDXLTurboModel {
           #_create_pipeline()
       }

       class SD15Model {
           #_create_pipeline()
       }

       BaseModel <|-- ZImageTurboModel
       BaseModel <|-- FluxModel
       BaseModel <|-- Flux2KleinModel
       BaseModel <|-- QwenImageModel
       BaseModel <|-- SDXLTurboModel
       CompelPromptMixin <|-- SDXLModel
       CompelPromptMixin <|-- SD15Model
       BaseModel <|-- SDXLModel
       BaseModel <|-- SD15Model

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
   * - ``enable_vae_slicing``
     - Enable VAE slicing for reduced memory usage
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

Models for TV commercial campaign management: campaigns, polymorphic ad units,
scripts, multi-agent adaptation pipeline, and storyboard generation.

.. mermaid::

   erDiagram
       Campaign {
           bigint id PK
           varchar job_id UK
           varchar script_title
           varchar client_name
           varchar brand_name
           varchar product_name
           json original_script_data
           timestamp created_at
           timestamp updated_at
       }

       AdUnit {
           bigint id PK
           bigint campaign_id FK
           varchar ad_unit_type
           varchar origin_or_adaptation
           varchar code
           varchar title
           bigint region_id FK
           bigint country_id FK
           bigint language_id FK
           bigint llm_model_id FK
           bigint source_ad_unit_id FK
           bool use_pipeline
           json concept_brief
           json cultural_brief
           json evaluation_history
           json pipeline_metadata
           varchar status
           varchar celery_task_id
           text error_message
           timestamp created_at
           timestamp started_at
           timestamp completed_at
           timestamp updated_at
       }

       VideoAdUnit {
           bigint adunit_ptr_id PK_FK
           decimal duration
           text visual_style_prompt
       }

       AdUnitScriptRow {
           bigint id PK
           bigint ad_unit_id FK
           int order_index
           varchar shot_number
           varchar timecode
           text visual_text
           text audio_text
       }

       Storyboard {
           bigint id PK
           bigint video_ad_unit_id FK
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
           bigint storyboard_id FK
           bigint script_row_id FK
           bigint diffusion_job_id FK
           int image_index
       }

       Campaign ||--o{ AdUnit : "contains"
       AdUnit ||--o| VideoAdUnit : "extends"
       AdUnit ||--o{ AdUnitScriptRow : "has rows"
       AdUnit ||--o| AdUnit : "source_ad_unit"
       VideoAdUnit ||--o{ Storyboard : "generates"
       Storyboard ||--o{ StoryboardImage : "produces"
       AdUnitScriptRow ||--o{ StoryboardImage : "source for"

**Campaign**
   Top-level campaign container. Represents a campaign/project before any
   adaptations or storyboard generation. Created via JSON import.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``job_id``
        - varchar(100)
        - Internal tracking ID (e.g., 'ACME-2024-001'), unique
      * - ``script_title``
        - varchar(200)
        - Campaign/script title
      * - ``client_name``
        - varchar(200)
        - Client name
      * - ``brand_name``
        - varchar(200)
        - Brand name
      * - ``product_name``
        - varchar(200)
        - Product name
      * - ``original_script_data``
        - json
        - Original script content as JSON

**AdUnit**
   Polymorphic base class for all ad unit types using Django multi-table inheritance.
   Child models (VideoAdUnit, future AudioAdUnit/PrintAdUnit) extend this base with
   media-specific fields.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``campaign``
        - FK
        - Parent campaign (CASCADE on delete)
      * - ``ad_unit_type``
        - varchar(20)
        - Type: VIDEO, AUDIO, PRINT (set automatically by child class)
      * - ``origin_or_adaptation``
        - varchar(20)
        - ORIGIN or ADAPTATION
      * - ``code``
        - varchar(50)
        - Version code (e.g., 'US-EN-001', 'DE-DE-002')
      * - ``title``
        - varchar(200)
        - Descriptive title
      * - ``region``
        - FK
        - Target region for adaptations (PROTECT on delete)
      * - ``country``
        - FK
        - Target country for adaptations (PROTECT on delete)
      * - ``language``
        - FK
        - Target language for adaptations (PROTECT on delete)
      * - ``llm_model``
        - FK
        - Override language's primary LLM model (PROTECT on delete)
      * - ``source_ad_unit``
        - FK (self)
        - Source ad unit this was adapted from (SET_NULL on delete)
      * - ``use_pipeline``
        - bool
        - Use multi-agent pipeline for adaptation
      * - ``concept_brief``
        - json
        - Concept extraction output from pipeline
      * - ``cultural_brief``
        - json
        - Cultural research output from pipeline
      * - ``evaluation_history``
        - json
        - Chronological evaluation results from pipeline
      * - ``pipeline_metadata``
        - json
        - Pipeline timing, model info, and revision counts
      * - ``status``
        - varchar(30)
        - Status: pending, processing, completed, failed, concept_analysis, cultural_analysis, writing, format_evaluation, cultural_evaluation, concept_evaluation, revising
      * - ``celery_task_id``
        - varchar(255)
        - Celery task ID for async processing
      * - ``error_message``
        - text
        - Error message if job failed
      * - ``started_at``
        - timestamp
        - When processing started
      * - ``completed_at``
        - timestamp
        - When processing finished

**VideoAdUnit**
   Video-specific ad unit extending AdUnit via multi-table inheritance. Can be either
   an origin unit or an adaptation targeting specific markets.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``duration``
        - decimal(6,2)
        - Duration in seconds
      * - ``visual_style_prompt``
        - text
        - Common visual style applied to all script rows

**AdUnitScriptRow**
   A single row in the two-column A/V script format. Points to the base AdUnit class,
   allowing script rows to work with any ad unit type via multi-table inheritance.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``ad_unit``
        - FK
        - Parent ad unit (CASCADE on delete)
      * - ``order_index``
        - int
        - Row order in script (0-indexed), unique per ad unit
      * - ``shot_number``
        - varchar(10)
        - Shot/scene number
      * - ``timecode``
        - varchar(20)
        - Timecode (HH:MM:SS:FF or HH:MM:SS.mmm)
      * - ``visual_text``
        - text
        - Visual/video column content
      * - ``audio_text``
        - text
        - Audio/dialogue column content

**Storyboard**
   Coordinates storyboard generation for a VideoAdUnit. Creates one DiffusionJob per
   script row (multiplied by ``images_per_row``). Multiple storyboards can exist per
   VideoAdUnit with different configurations.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``video_ad_unit``
        - FK
        - Video ad unit to generate storyboard for (CASCADE on delete)
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
   Junction table linking Storyboard, AdUnitScriptRow, and DiffusionJob. Allows
   multiple images per row and multiple storyboard runs per video ad unit.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``storyboard``
        - FK
        - Parent storyboard (CASCADE on delete)
      * - ``script_row``
        - FK
        - Source script row (CASCADE on delete)
      * - ``diffusion_job``
        - OneToOne FK
        - Image generation job (CASCADE on delete)
      * - ``image_index``
        - int
        - Image sequence within the row (for multiple images per row)

Core App (cw.core)
~~~~~~~~~~~~~~~~~~~

Reference data models for regions, countries, languages, and LLM models used
by the multi-agent adaptation pipeline.

.. mermaid::

   erDiagram
       LLMModel {
           bigint id PK
           varchar model_id UK
           varchar name
           text notes
           bool is_active
           bool load_in_4bit
           timestamp created_at
           timestamp updated_at
       }

       Region {
           bigint id PK
           varchar code UK
           varchar name
           text description
           json insights
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       Country {
           bigint id PK
           varchar code UK
           varchar name
           bigint default_language_id FK
           json insights
           text notes
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       Language {
           bigint id PK
           varchar code UK
           varchar name
           varchar base_language
           bigint primary_model_id FK
           json insights
           text notes
           bool is_active
           timestamp created_at
           timestamp updated_at
       }

       CountryRegion {
           bigint id PK
           bigint country_id FK
           bigint region_id FK
       }

       CountryLanguage {
           bigint id PK
           bigint country_id FK
           bigint language_id FK
           bool is_primary
       }

       LanguageAlternativeModel {
           bigint id PK
           bigint language_id FK
           bigint llmmodel_id FK
       }

       LLMModel ||--o{ Language : "primary for"
       LLMModel ||--o{ LanguageAlternativeModel : "alternative for"
       Language ||--o{ LanguageAlternativeModel : "has alternatives"
       Language ||--o{ Country : "default for"
       Country ||--o{ CountryRegion : "belongs to"
       Region ||--o{ CountryRegion : "contains"
       Country ||--o{ CountryLanguage : "speaks"
       Language ||--o{ CountryLanguage : "spoken in"

**LLMModel**
   HuggingFace language model configuration for text generation in adaptation tasks.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``model_id``
        - varchar(200)
        - HuggingFace model ID (e.g., 'Qwen/Qwen2.5-7B-Instruct'), unique
      * - ``name``
        - varchar(100)
        - Friendly display name
      * - ``notes``
        - text
        - Notes about model capabilities, strengths, or limitations
      * - ``is_active``
        - bool
        - Whether this model is available for use
      * - ``load_in_4bit``
        - bool
        - Load model with 4-bit quantization (requires bitsandbytes)

**Region**
   Cultural/market grouping with regional insights (e.g., North America, DACH, LATAM).

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``code``
        - varchar(20)
        - Short code (e.g., 'NA', 'NORDICS', 'DACH'), unique
      * - ``name``
        - varchar(100)
        - Display name (e.g., 'North America')
      * - ``description``
        - text
        - Region description and scope
      * - ``insights``
        - json
        - Regional cultural patterns: [{heading, points[]}]
      * - ``is_active``
        - bool
        - Enable/disable region

**Country**
   Political/regulatory entity with country-specific insights and regulatory requirements.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``code``
        - varchar(2)
        - ISO 3166-1 alpha-2 code (e.g., 'US', 'CA', 'SE'), unique
      * - ``name``
        - varchar(100)
        - Official country name
      * - ``default_language``
        - FK
        - Primary/default language for this country (PROTECT on delete)
      * - ``insights``
        - json
        - Country-specific regulatory and cultural rules: [{heading, points[]}]
      * - ``notes``
        - text
        - Additional notes
      * - ``is_active``
        - bool
        - Enable/disable country

**Language**
   Language variant with locale code and LLM model recommendations for adaptation.

   .. list-table::
      :header-rows: 1
      :widths: 25 15 60

      * - Field
        - Type
        - Description
      * - ``code``
        - varchar(10)
        - ISO 639 + country locale (e.g., 'en-US', 'fr-CA'), unique
      * - ``name``
        - varchar(100)
        - Display name (e.g., 'English (United States)')
      * - ``base_language``
        - varchar(10)
        - ISO 639-1 base language code (e.g., 'en', 'fr', 'de')
      * - ``primary_model``
        - FK
        - Recommended LLM model for this language (PROTECT on delete)
      * - ``insights``
        - json
        - Language-specific localization guidance: [{heading, points[]}]
      * - ``notes``
        - text
        - Notes about language-specific considerations
      * - ``is_active``
        - bool
        - Whether this language is available for adaptations

Cross-App References
~~~~~~~~~~~~~~~~~~~~

The ``tvspots`` app references models from the ``diffusion`` and ``core`` apps:

**tvspots → diffusion:**

- ``Storyboard.diffusion_model`` → ``DiffusionModel`` (PROTECT)
- ``Storyboard.lora_model`` → ``LoraModel`` (SET_NULL)
- ``StoryboardImage.diffusion_job`` → ``DiffusionJob`` (CASCADE)

**tvspots → core:**

- ``AdUnit.region`` → ``Region`` (PROTECT)
- ``AdUnit.country`` → ``Country`` (PROTECT)
- ``AdUnit.language`` → ``Language`` (PROTECT)
- ``AdUnit.llm_model`` → ``LLMModel`` (PROTECT)

This creates a clean separation where ``diffusion`` handles image generation,
``core`` provides reference data, and ``tvspots`` handles TV commercial workflow
orchestration.

Observability
-------------

Logging
~~~~~~~

All components use structured JSON logging:

.. code-block:: text

    logs/
    ├── django.log           # Django server logs
    ├── celery.log           # Celery general logs
    ├── tasks.log            # Task execution logs (all workers)
    └── worker_default.log   # Default queue worker

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
