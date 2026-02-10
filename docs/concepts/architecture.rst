Architecture Overview
=====================

This page explains how the system fits together: processes, apps, libraries, data flow, and configuration.

Process Model
-------------

The application runs as 5 concurrent processes, defined in the ``Procfile`` and managed by Honcho:

.. mermaid::

   graph LR
       subgraph Docker["Docker Compose"]
           PG["PostgreSQL 17<br/>:5435"]
           VK["Valkey<br/>:6379"]
           LK["Loki<br/>:3100"]
           AL["Alloy"]
           GR["Grafana<br/>:3000"]
       end
       DJ["Django<br/>:8000"]
       CW["Celery Worker<br/>(solo pool)"]
       FL["Flower<br/>:5555"]
       TW["Tailwind<br/>(watcher)"]

       DJ -->|reads/writes| PG
       DJ -->|queues tasks| VK
       CW -->|polls tasks| VK
       CW -->|stores results| PG
       FL -->|monitors| VK
       AL -->|ships logs| LK
       GR -->|queries| LK

.. list-table::
   :header-rows: 1
   :widths: 15 55 15

   * - Process
     - Command
     - Port
   * - **docker**
     - ``docker compose up`` — PostgreSQL, Valkey, Loki, Alloy, Grafana
     - Various
   * - **django**
     - ``uv run manage.py runserver``
     - 8000
   * - **worker**
     - Celery worker on ``default`` queue (``--pool=solo``)
     - —
   * - **flower**
     - Celery task monitor
     - 5555
   * - **tailwind**
     - Tailwind CSS watcher (rebuilds on file change)
     - —

The Celery worker uses the ``solo`` pool — a single-threaded, non-forking worker. This is intentional: it prevents concurrent GPU model loading, ensuring only one diffusion model occupies VRAM at a time.

Docker Services
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Service
     - Port
     - Purpose
   * - **PostgreSQL 17**
     - 5435
     - Primary database for all Django models and Celery result storage
   * - **Valkey**
     - 6379
     - Redis-compatible broker for Celery task queuing
   * - **Loki**
     - 3100
     - Log aggregation backend (stores structured JSON logs)
   * - **Alloy**
     - —
     - Observability collector that ships ``logs/*.log`` to Loki
   * - **Grafana**
     - 3000
     - Web UI for log search and visualization (anonymous login enabled for dev)

Project Structure
-----------------

The project uses a **src layout** for proper Python packaging:

.. code-block:: text

   generative-creative-lab/
   ├── src/cw/                  # Main Python package
   │   ├── core/                # LLM models, prompt templates, pipeline settings
   │   ├── audiences/           # Regions, countries, languages, segments, personas
   │   ├── diffusion/           # Diffusion models, LoRAs, prompts, generation jobs
   │   ├── tvspots/             # Campaigns, ad units, scripts, storyboards, video analysis
   │   ├── lib/                 # Supporting library modules (see below)
   │   └── settings.py          # Django settings (Celery, logging, apps)
   ├── data/                    # JSON configuration and seed data
   ├── media/                   # Generated images and uploaded files
   ├── logs/                    # Structured JSON log files
   ├── Procfile                 # Process definitions for Honcho
   ├── docker-compose.yml       # Infrastructure services
   └── manage.py                # Django management script

Django Apps
^^^^^^^^^^^

Four apps, each with a focused domain:

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - App
     - Key Models
     - Purpose
   * - **core**
     - LLMModel, PromptTemplate, PipelineSettings
     - LLM model registry, Jinja2 prompt templates (database-backed with versioning), and pipeline default configuration
   * - **diffusion**
     - DiffusionModel, LoraModel, Prompt, DiffusionJob
     - Diffusion model catalog, LoRA adapters, prompt creation/enhancement, and image generation jobs
   * - **audiences**
     - Region, Country, Language, Segment, Persona
     - Geographic hierarchy (Region → Country → Language) and non-geographic segmentation (Demographic/Behavioral/Psychographic) with persona composition
   * - **tvspots**
     - Brand, Campaign, VideoAdUnit, AdUnitScriptRow, Storyboard, StoryboardImage
     - TV spot campaigns, origin/adaptation ad units, script management, multi-agent pipeline, storyboard generation, and video analysis

Library Modules
^^^^^^^^^^^^^^^

Supporting code lives in ``src/cw/lib/``, separate from Django app logic:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Module
     - Purpose
   * - **models/**
     - Diffusion model implementations: BaseModel, mixins, 7 concrete models, ModelFactory (see :doc:`diffusion-models`)
   * - **pipeline/**
     - LangGraph-based adaptation pipeline: state, schemas, 7 nodes, graph construction, model loader (see :doc:`adaptation-pipeline`)
   * - **prompts/**
     - Jinja2 template rendering from database (``render_prompt()``) with caching
   * - **loras/**
     - LoRA filtering by base architecture and optional theme
   * - **video_analysis/**
     - Video processing: scene detection, transcription, object detection, visual style, sentiment, audience insights
   * - **security/**
     - Video upload validation (MIME type, codec, size)
   * - **prompt_enhancer.py**
     - Three prompt enhancement strategies: rule-based, local HF (Qwen2.5-3B), Anthropic API
   * - **config.py**
     - ``PresetsConfig``: loads and validates ``data/presets.json``
   * - **civitai.py**
     - CivitAI integration: parse AIR URNs, auto-download LoRA files
   * - **insights.py**
     - Hierarchical insights composition (Region → Country → Language → Persona)
   * - **storyboard.py**
     - Generates image prompts from script rows and creates DiffusionJobs
   * - **adaptation.py**
     - Adaptation pipeline utilities: state building, model resolution, context composition

Data Flow
---------

Image Generation
^^^^^^^^^^^^^^^^

.. mermaid::

   sequenceDiagram
       participant User as Admin UI
       participant Django
       participant Celery as Celery Worker
       participant Model as Diffusion Model
       participant FS as media/diffusion/

       User->>Django: Create Prompt + DiffusionJob
       Django->>Celery: Auto-queue generate_images_task
       Celery->>Celery: Load model (warm cache)
       Celery->>Celery: Apply LoRA (if set)
       Celery->>Model: Generate image(s)
       Model->>FS: Save to media/diffusion/
       Celery->>Django: Update job status + metadata
       User->>Django: View results in admin

TV Spot Adaptation
^^^^^^^^^^^^^^^^^^

.. mermaid::

   sequenceDiagram
       participant User as Admin UI
       participant Django
       participant Celery as Celery Worker
       participant LLM as LLM Models
       participant Diff as Diffusion Model

       User->>Django: Create Campaign + Origin VideoAdUnit
       User->>Django: Create Adaptation VideoAdUnit
       Django->>Celery: Auto-queue create_adaptation_task
       Celery->>LLM: Concept extraction
       Celery->>LLM: Cultural research
       Celery->>LLM: Script writing
       Celery->>LLM: Evaluation gates (format, cultural, concept, brand)
       Celery->>Django: Save briefs + adapted script rows
       User->>Django: Create Storyboard
       Django->>Celery: Auto-queue generate_storyboard_task
       Celery->>Diff: Generate frame images
       Celery->>Django: Update storyboard progress
       User->>Django: View storyboard frames

Configuration Layers
--------------------

The system has four configuration layers, from most general to most specific:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Layer
     - Source
     - What it configures
   * - **Environment**
     - ``.env``
     - Database credentials, API keys (Anthropic, CivitAI), model base path
   * - **Presets**
     - ``data/presets.json``
     - Diffusion model catalog: steps, guidance, dtype, scheduler, LoRA definitions, per-model settings flags
   * - **Django Settings**
     - ``src/cw/settings.py``
     - Celery config (broker, queues, time limits), logging, installed apps, Unfold admin
   * - **Database**
     - Django admin UI
     - Prompt templates (versioned), pipeline settings (per-node LLM defaults), audience data, brands

Seed data files in ``data/`` bootstrap the database: ``presets.json``, ``llm_models.json``, ``regions.json``, ``countries.json``, ``languages.json``, ``prompt_templates.json``, ``segments.json``, ``personas.json``, ``brands.json``, and their M2M relationship files. All are imported via management commands (see :doc:`/guides/operations/data-import-export`).

Celery Task Architecture
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Task
     - Queue
     - Purpose
   * - ``enhance_prompt_task``
     - enhancement
     - Enhance a prompt using rule-based, HF, or Anthropic method
   * - ``generate_images_task``
     - default
     - Generate image(s) for a DiffusionJob
   * - ``create_adaptation_task``
     - default
     - Run the 7-node multi-agent adaptation pipeline
   * - ``generate_storyboard_task``
     - default
     - Create prompts and DiffusionJobs for storyboard frames

The worker uses a **module-level model cache** — a dictionary that keeps the most recently used diffusion model (or LLM enhancer) loaded in memory. When a new model is needed, the old one is evicted and VRAM is freed. This avoids re-loading the same model for consecutive jobs.

Time limits: 1 hour hard limit, 55 minutes soft limit. Results stored in the Django database via ``django-celery-results``.
