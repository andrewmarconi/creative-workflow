Celery Tasks & Queues
=====================

Reference for all Celery tasks, queue configuration, and worker behavior.

Task Reference
--------------

enhance_prompt_task
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.diffusion.tasks.enhance_prompt_task(prompt_id)``
   * - Queue
     - ``enhancement``
   * - Arguments
     - ``prompt_id`` (int) --- Prompt record ID
   * - Returns
     - ``{status, prompt_id, enhanced_preview, method}``
   * - Idempotent
     - Yes --- skips if prompt already has ``enhanced_prompt``

Enhances a diffusion prompt using a local LLM (Qwen2.5-3B-Instruct). Reads ``enhancement_style`` and ``creativity`` from the Prompt record. The enhancer instance is cached in ``_enhancer_cache`` between invocations.

generate_images_task
^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.diffusion.tasks.generate_images_task(job_id)``
   * - Queue
     - ``default``
   * - Arguments
     - ``job_id`` (int) --- DiffusionJob record ID
   * - Returns
     - ``{status, job_id, images_count, paths}``

Primary image generation task. Execution sequence:

1. Evict prompt enhancer and pipeline LLM from VRAM
2. Load diffusion model (cached between tasks via ``_model_cache``)
3. Load LoRA if specified (auto-downloads from CivitAI if needed)
4. Generate N images sequentially (randomized seed per image)
5. Save to ``media/diffusion/`` as JPEG (quality 95)
6. Build comprehensive generation metadata
7. Unload LoRA to reset state

**Status flow**: ``pending`` → ``processing`` → ``completed`` | ``failed``

download_lora_task
^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.diffusion.tasks.download_lora_task(lora_id)``
   * - Queue
     - ``default``
   * - Arguments
     - ``lora_id`` (int) --- LoraModel record ID
   * - Returns
     - ``{status, lora_id, path}``

Downloads a LoRA from CivitAI using the model's AIR URN. Saves to ``{MODEL_BASE_PATH}/loras/civitai_{version_id}.safetensors``. Skips if the file already exists.

create_adaptation_task
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.tvspots.tasks.create_adaptation_task(video_ad_unit_id)``
   * - Queue
     - ``default``
   * - Arguments
     - ``video_ad_unit_id`` (int) --- VideoAdUnit record ID
   * - Returns
     - ``{status, video_ad_unit_id, pipeline}``

Runs the multi-agent adaptation pipeline (LangGraph) for a VideoAdUnit. The pipeline executes concept extraction, cultural research, script writing, and four evaluation gates. On failure, sets the ad unit status to ``failed`` with an error message.

See :doc:`/concepts/adaptation-pipeline` for the full pipeline architecture.

generate_storyboard_task
^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.tvspots.tasks.generate_storyboard_task(storyboard_id, enhance_prompts=True)``
   * - Queue
     - ``default``
   * - Arguments
     - ``storyboard_id`` (int), ``enhance_prompts`` (bool, default ``True``)
   * - Returns
     - ``{status, storyboard_id, num_prompts, num_jobs, job_ids}``

Generates storyboard frames from script rows. Execution sequence:

1. Evict pipeline LLM from VRAM
2. Generate diffusion prompts from script rows (optionally LLM-enhanced)
3. Clear GPU cache
4. Create DiffusionJob + StoryboardImage records (1280x720)
5. Queue each job to the ``default`` queue
6. Return array of job IDs for tracking

analyze_video_task
^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75

   * - Signature
     - ``cw.tvspots.tasks.analyze_video_task(ad_unit_media_id)``
   * - Queue
     - ``default``
   * - Arguments
     - ``ad_unit_media_id`` (int) --- AdUnitMedia record ID
   * - Returns
     - ``{status, media_id, result_id, processing_time}``
   * - Retries
     - 3 (exponential backoff: 60s x 2^attempt)

10-phase video analysis pipeline with progress tracking via ``self.update_state()``:

.. list-table::
   :header-rows: 1
   :widths: 15 20 65

   * - Progress
     - Phase
     - Tool
   * - 0--10%
     - Metadata extraction
     - PyAV (duration, resolution, FPS, audio channels)
   * - 10--30%
     - Scene detection
     - PySceneDetect
   * - 30--50%
     - Transcription
     - Whisper Large v3
   * - 50--70%
     - Visual analysis
     - YOLO v8x + OpenCV (objects, style, colors)
   * - 70--90%
     - Script generation
     - Scene-to-script mapping
   * - 90--95%
     - Audience insights
     - LLM (Qwen 7B)
   * - 95--100%
     - Finalization
     - Save to database

Queue Configuration
-------------------

Two queues handle all tasks:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Queue
     - Exchange
     - Tasks
   * - ``default``
     - ``default``
     - ``generate_images_task``, ``download_lora_task``, ``create_adaptation_task``, ``generate_storyboard_task``, ``analyze_video_task``
   * - ``enhancement``
     - ``enhancement``
     - ``enhance_prompt_task``

Task routing is configured in ``settings.py``:

.. code-block:: python

   CELERY_TASK_ROUTES = {
       "cw.diffusion.tasks.enhance_prompt_task": {"queue": "enhancement"},
       "cw.diffusion.tasks.generate_images_task": {"queue": "default"},
   }

Tasks without explicit routing (TV Spots tasks) use the ``default`` queue.

Worker Configuration
--------------------

Pool
^^^^

Workers use the ``solo`` pool (single-threaded):

.. code-block:: bash

   uv run celery -A cw worker -Q default

The solo pool is required because:

- **GPU safety** --- prevents concurrent model loading that would exhaust VRAM
- **macOS MPS** --- ``fork()`` is not compatible with the Metal Performance Shaders backend
- **Sequential execution** --- one task at a time ensures predictable memory usage

Time Limits
^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Setting
     - Value
     - Effect
   * - ``CELERY_TASK_TIME_LIMIT``
     - 3600s (1 hour)
     - Hard kill --- worker process terminated
   * - ``CELERY_TASK_SOFT_TIME_LIMIT``
     - 3300s (55 minutes)
     - Raises ``SoftTimeLimitExceeded`` for graceful shutdown

Result Storage
^^^^^^^^^^^^^^

Task results are stored in the Django ORM via ``django-celery-results``:

- Backend: ``django-db``
- Model: ``django_celery_results.TaskResult``
- Extended results enabled (``CELERY_RESULT_EXTENDED = True``)
- Viewable in Django admin under **Celery > Task Results**

Broker
^^^^^^

Valkey/Redis on database index 2:

.. code-block:: text

   redis://{VALKEY_HOST}:{VALKEY_PORT}/2

Serialization is JSON-only (``CELERY_TASK_SERIALIZER = "json"``). Timezone is UTC.

Model Caching
-------------

Module-level caches keep models warm between task invocations, avoiding expensive reload cycles.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Cache
     - Location
     - Behavior
   * - ``_model_cache``
     - ``diffusion/tasks.py``
     - Keeps one diffusion model loaded. Evicts the previous model when a different model is requested.
   * - ``_enhancer_cache``
     - ``diffusion/tasks.py``
     - Keeps HFPromptEnhancer (Qwen2.5-3B) loaded between enhancement tasks.

**VRAM management** --- before image generation, the enhancer cache and pipeline LLM are evicted:

1. ``_evict_enhancer()`` clears the enhancer cache
2. ``_evict_pipeline_model()`` clears the ``PipelineModelLoader`` singleton
3. ``gc.collect()`` + ``torch.cuda.empty_cache()`` / ``torch.mps.empty_cache()``

This ensures only one large model occupies VRAM at a time.

Retry Behavior
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Task
     - Retries
     - Strategy
   * - ``analyze_video_task``
     - 3
     - Exponential backoff: 60s x 2^attempt
   * - All other tasks
     - 0
     - No automatic retry; errors set job status to ``failed``

All tasks catch exceptions and persist error information to the database (``error_message`` field on the job/ad-unit record).

Starting Workers
----------------

Single worker handling all queues:

.. code-block:: bash

   uv run celery -A cw worker -Q default,enhancement

Separate workers per queue:

.. code-block:: bash

   # Terminal 1: image generation and pipeline tasks
   uv run celery -A cw worker -Q default

   # Terminal 2: prompt enhancement
   uv run celery -A cw worker -Q enhancement

Monitor with Flower:

.. code-block:: bash

   uv run celery -A cw flower --port=5555

The recommended approach is ``./start.sh`` or ``uv run honcho start``, which launches all processes defined in the Procfile.
