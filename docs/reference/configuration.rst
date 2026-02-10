Configuration
=============

All configuration surfaces: environment variables, data files, Django settings, and Docker services.

Environment Variables
---------------------

Set in ``.env`` at the project root. Variables with defaults shown can be omitted for local development.

Database
^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``POSTGRES_DB``
     - ``cw``
     - Database name
   * - ``POSTGRES_USER``
     - ``cw``
     - Database user
   * - ``POSTGRES_PASSWORD``
     - ``cw_dev``
     - Database password
   * - ``POSTGRES_HOST``
     - ``localhost``
     - Database host
   * - ``POSTGRES_PORT``
     - ``5435``
     - Database port (non-standard to avoid conflicts)

Broker
^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``VALKEY_HOST``
     - ``localhost``
     - Valkey/Redis host
   * - ``VALKEY_PORT``
     - ``6379``
     - Valkey/Redis port

Application
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Variable
     - Default
     - Description
   * - ``DJANGO_SECRET_KEY``
     - *(required)*
     - Django secret key for sessions and CSRF
   * - ``DJANGO_DEBUG``
     - ``True``
     - Debug mode (set ``False`` in production)
   * - ``ANTHROPIC_API_KEY``
     - *(empty)*
     - Anthropic API key for LLM prompt enhancement
   * - ``CIVITAI_API_KEY``
     - *(empty)*
     - CivitAI API key for LoRA auto-downloads
   * - ``MODEL_BASE_PATH``
     - ``{PROJECT_ROOT}/models``
     - Base directory for local ``.safetensors`` model files

Video Upload
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Variable
     - Default
     - Description
   * - ``VIDEO_MAX_UPLOAD_SIZE_BYTES``
     - ``524288000``
     - Maximum upload size (500 MB)

Presets Configuration
---------------------

``data/presets.json`` defines diffusion models and LoRAs. Synced to the database via ``import_presets``.

Top-Level Structure
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   {
     "models": [ ... ],
     "loras": [ ... ]
   }

Model Fields
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``slug``
     - string
     - Unique identifier (e.g., ``flux1_dev``)
   * - ``label``
     - string
     - Display name
   * - ``path``
     - string
     - HuggingFace repo ID or local ``.safetensors`` path
   * - ``pipeline``
     - string
     - Diffusers pipeline class (e.g., ``FluxPipeline``)
   * - ``base_architecture``
     - string
     - Model family: ``flux1``, ``sdxl``, ``sd15``, ``zimage``, ``qwen``
   * - ``settings``
     - object
     - Generation parameters and behavior flags (see below)

Model Settings
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Setting
     - Type
     - Description
   * - ``steps``
     - int
     - Default inference steps
   * - ``guidance_scale``
     - float
     - Default classifier-free guidance strength
   * - ``default_width``
     - int
     - Default image width (pixels)
   * - ``default_height``
     - int
     - Default image height (pixels)
   * - ``max_pixels``
     - int
     - Maximum total pixels (width x height)
   * - ``dtype``
     - string
     - Tensor type: ``bfloat16`` or ``float16``
   * - ``supports_negative_prompt``
     - bool
     - Whether the model uses negative prompts
   * - ``scheduler``
     - string
     - Diffusers scheduler class name
   * - ``token_window``
     - int
     - Maximum prompt tokens (77 for CLIP, 512 for Flux)
   * - ``vram_usage``
     - int
     - Estimated VRAM in MB

Behavior Flags
^^^^^^^^^^^^^^

Optional flags within ``settings`` that enable special model behavior:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Flag
     - Applicable Models
     - Description
   * - ``force_default_guidance``
     - Turbo models
     - Ignore user guidance_scale, use model default
   * - ``enable_debug_logging``
     - Any
     - Enable debug print statements via ``DebugLoggingMixin``
   * - ``use_sequential_cpu_offload``
     - CUDA models
     - Use sequential CPU offload (more memory-efficient)
   * - ``max_sequence_length``
     - Flux variants
     - Maximum context length for prompt encoding (512)
   * - ``load_in_8bit``
     - Qwen
     - 8-bit quantization to reduce VRAM usage

LoRA Fields
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``label``
     - string
     - Display name
   * - ``base_architecture``
     - string
     - Target model family (must match model's architecture)
   * - ``theme``
     - string
     - Category tag (e.g., ``anime``, ``photorealistic``, ``comic``)
   * - ``air``
     - string
     - CivitAI AIR URN: ``urn:air:{arch}:lora:civitai:{model_id}@{version_id}``
   * - ``prompt``
     - string
     - Trigger words appended when LoRA is active
   * - ``negative_prompt``
     - string
     - Negative prompt to use with this LoRA
   * - ``notes``
     - string
     - Metadata or CivitAI stats

LoRA Settings
^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Setting
     - Type
     - Description
   * - ``strength``
     - float
     - LoRA weight multiplier (typical range 0.5--1.3)
   * - ``guidance_scale``
     - float
     - Recommended guidance when using this LoRA
   * - ``clip_skip``
     - int
     - CLIP layer skip (1--2) for SD models

Django Settings
---------------

Key settings in ``src/cw/settings.py``.

Celery
^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Value
   * - ``CELERY_BROKER_URL``
     - ``redis://{VALKEY_HOST}:{VALKEY_PORT}/2``
   * - ``CELERY_RESULT_BACKEND``
     - ``django-db`` (Django ORM via ``django-celery-results``)
   * - ``CELERY_RESULT_EXTENDED``
     - ``True``
   * - ``CELERY_WORKER_POOL``
     - ``solo`` (single-threaded for GPU safety)
   * - ``CELERY_TASK_TIME_LIMIT``
     - ``3600`` (1 hour hard limit)
   * - ``CELERY_TASK_SOFT_TIME_LIMIT``
     - ``3300`` (55 minutes soft limit)
   * - ``CELERY_TASK_SERIALIZER``
     - ``json``
   * - ``CELERY_TIMEZONE``
     - ``UTC``

Logging
^^^^^^^

JSON-structured logging via ``pythonjsonlogger.JsonFormatter``. Rotating file handlers with 10 MB limit and 5 backups per file.

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 30

   * - Logger
     - Handler
     - Level
     - Description
   * - ``django``
     - ``django_file``
     - INFO
     - Server requests and ORM
   * - ``celery``
     - ``celery_file``
     - INFO
     - Worker lifecycle and routing
   * - ``cw.diffusion.tasks``
     - ``tasks_file``
     - INFO
     - Image generation tasks
   * - ``cw.tvspots.tasks``
     - ``tasks_file``
     - INFO
     - Adaptation and storyboard tasks
   * - ``cw.lib.adaptation``
     - ``tasks_file``
     - DEBUG
     - Pipeline execution
   * - ``cw.lib.models``
     - ``tasks_file``
     - DEBUG
     - Diffusion model loading
   * - ``cw.lib.prompt_enhancer``
     - ``tasks_file``
     - DEBUG
     - Prompt enhancement
   * - ``cw.lib.storyboard``
     - ``tasks_file``
     - DEBUG
     - Storyboard generation
   * - ``cw.lib.civitai``
     - ``tasks_file``
     - DEBUG
     - CivitAI LoRA downloads
   * - ``cw.lib.security``
     - ``tasks_file``
     - INFO
     - File upload validation

Video Upload
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Value
   * - ``VIDEO_ALLOWED_EXTENSIONS``
     - ``.mp4``, ``.mov``, ``.avi``, ``.mkv``, ``.webm``
   * - ``VIDEO_ALLOWED_MIME_TYPES``
     - ``video/mp4``, ``video/quicktime``, ``video/x-msvideo``, ``video/x-matroska``, ``video/webm``
   * - ``VIDEO_VERIFY_MIME_CONTENT``
     - ``True``
   * - ``VIDEO_VALIDATE_HEADERS``
     - ``True``
   * - ``VIDEO_SANITIZE_FILENAMES``
     - ``True``

Docker Compose Services
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 15 25 10 50

   * - Service
     - Image
     - Port
     - Purpose
   * - ``postgres``
     - ``postgres:17``
     - 5435
     - PostgreSQL database
   * - ``valkey``
     - ``valkey/valkey:latest``
     - 6379
     - Celery broker (Redis-compatible)
   * - ``loki``
     - ``grafana/loki:latest``
     - 3100
     - Log aggregation backend
   * - ``alloy``
     - ``grafana/alloy:latest``
     - ---
     - Log collector (ships ``logs/*.log`` to Loki)
   * - ``grafana``
     - ``grafana/grafana:latest``
     - 3000
     - Log search UI (anonymous login enabled)

Named volumes: ``postgres_data``, ``valkey_data``, ``loki_data``, ``grafana_data``.

Health checks are configured for ``postgres`` (``pg_isready``) and ``valkey`` (``valkey-cli ping``). Use ``./start.sh`` to wait for healthy containers before starting Django.
