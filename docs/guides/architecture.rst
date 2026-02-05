System Architecture
===================

This guide provides a comprehensive overview of Creative Workflow's architecture,
including the process model, data flow, and design patterns used throughout the system.

.. contents:: Table of Contents
   :local:
   :depth: 2

System Overview
---------------

Creative Workflow is a Django + Celery application for multi-model diffusion image
generation. The system is designed around asynchronous task processing to handle
GPU-intensive operations without blocking the web interface.

.. mermaid::

   flowchart TB
       subgraph cw["Creative Workflow"]
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

Creative Workflow runs four concurrent processes, defined in the ``Procfile``
and launched via ``honcho start``:

.. mermaid::

   flowchart LR
       subgraph docker["docker"]
           pg["PostgreSQL :5435"]
           valkey["Valkey :6379"]
           subgraph observability["Observability"]
               loki["Loki :3100"]
               promtail["Promtail"]
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
       promtail --> loki
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

LoRAs can be auto-downloaded from CivitAI using AIR URNs. See
:doc:`lora-management` for details.

Model Architecture
------------------

Creative Workflow uses the **Template Method Pattern** for diffusion model
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

See :doc:`adding-models` for the complete guide.

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

Core Models
~~~~~~~~~~~

.. mermaid::

   erDiagram
       DiffusionModel {
           string label
           string slug PK
           string pipeline
           string path
           json settings
       }

       LoraModel {
           string label
           string base_architecture
           string civitai_air
           string prompt_suffix
           string theme
       }

       Prompt {
           string text
           string enhanced_text
           string negative_prompt
       }

       DiffusionJob {
           string status
           json images
           int width
           int height
           int steps
           float cfg
           int seed
       }

       DiffusionModel ||--o{ DiffusionJob : "model"
       LoraModel ||--o{ DiffusionJob : "lora"
       Prompt ||--o{ DiffusionJob : "prompt"

**DiffusionModel**
    Represents a diffusion model configuration. Synced from ``presets.json``
    via ``manage.py import_presets``.

**LoraModel**
    Represents a LoRA adapter with compatibility and trigger word settings.

**Prompt**
    Stores user prompts with optional enhancement tracking.

**DiffusionJob**
    Tracks generation jobs with all parameters and results.

TV Spots Models (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~

For TV spot workflow, additional models exist in ``cw.tvspots``:

- ``TvSpot`` - TV spot script metadata
- ``TvSpotVersion`` - Version/adaptation of a spot
- ``ScriptRow`` - Individual rows in a script
- ``AdaptationMarket`` - Market-specific adaptation rules
- ``StoryboardJob`` - Storyboard generation tracking

See :doc:`tvspots-workflow` for details.

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
- **Promtail** - Log collector shipping to Loki
- **Grafana** (:3000) - Web UI for log search and dashboards

Access Grafana at http://localhost:3000 (anonymous login enabled for dev).

See :doc:`observability` for detailed usage.

Related Documentation
---------------------

- :doc:`quickstart` - Getting started guide
- :doc:`configuration` - Configuration reference
- :doc:`adding-models` - Adding new diffusion models
- :doc:`/api/lib` - API reference for cw.lib
- :doc:`/api/diffusion` - API reference for cw.diffusion
