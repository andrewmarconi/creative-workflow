Troubleshooting
===============

Common issues and their solutions, organized by category.

Setup & Environment
-------------------

``ModuleNotFoundError: 'cw'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The package isn't installed in editable mode:

.. code-block:: bash

   uv pip install -e .

This is needed after a fresh clone or when the ``src/`` layout changes.

``DJANGO_SETTINGS_MODULE`` not set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensure you're running commands through ``uv run``:

.. code-block:: bash

   uv run manage.py migrate    # correct
   python manage.py migrate    # may fail without env setup

Missing static files in admin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run collectstatic:

.. code-block:: bash

   uv run manage.py collectstatic --noinput

Migration errors
^^^^^^^^^^^^^^^^

If you see migration conflicts after pulling changes:

.. code-block:: bash

   uv run manage.py migrate --run-syncdb

For persistent issues, check that PostgreSQL is running:

.. code-block:: bash

   docker compose ps

Model Loading
-------------

Out of memory (OOM)
^^^^^^^^^^^^^^^^^^^^

CUDA or MPS out-of-memory errors during model loading or generation:

- **Check warm cache** — ensure only one model is loaded at a time. The warm cache in ``tasks.py`` should evict the previous model automatically.
- **Reduce model size** — use ``load_in_8bit: true`` in presets.json for large models (e.g., Qwen-Image-2512)
- **Enable CPU offload** — set ``use_sequential_cpu_offload: true`` in the model's settings
- **Use a smaller model** — switch to a distilled variant (e.g., DreamShaper XL Lightning instead of Juggernaut XL)

Model not found
^^^^^^^^^^^^^^^

If a HuggingFace model fails to download:

- Check internet connectivity
- Verify the model path in ``data/presets.json`` matches the HuggingFace repo ID
- Run ``uv run manage.py preload_models`` to pre-download all models

Wrong dtype
^^^^^^^^^^^

If generation produces garbage or errors about tensor types:

- Ensure ``dtype`` is set correctly in presets.json (most models use ``bfloat16``)
- Some older models may need ``float16`` instead

LoRA Issues
-----------

Architecture mismatch
^^^^^^^^^^^^^^^^^^^^^

"LoRA not compatible" errors occur when a LoRA's ``base_architecture`` doesn't match the selected model:

- SDXL LoRAs only work with SDXL models (Juggernaut XL, DreamShaper XL, SDXL Turbo)
- SD15 LoRAs only work with SD 1.5 models (Realistic Vision)
- Check the LoRA's ``base_architecture`` field in presets.json

Missing trigger words
^^^^^^^^^^^^^^^^^^^^^

If a LoRA has no visible effect:

- Check the LoRA's ``prompt`` field in presets.json — trigger words must be present in the prompt
- Trigger words are automatically appended when the LoRA is active

CivitAI download failures
^^^^^^^^^^^^^^^^^^^^^^^^^

If auto-download fails:

- Verify ``CIVITAI_API_KEY`` is set in ``.env``
- Check the AIR URN format: ``urn:air:{ecosystem}:lora:civitai:{modelId}@{versionId}``
- CivitAI may rate-limit requests — retry after a few minutes
- Check ``logs/tasks.log`` for the ``cw.lib.civitai`` logger

Celery & Task Issues
--------------------

Tasks stuck in "pending"
^^^^^^^^^^^^^^^^^^^^^^^^

- Verify the Celery worker is running: ``uv run celery -A cw worker -Q default``
- Check that Valkey/Redis is running: ``docker compose ps``
- Check Flower at http://localhost:5555 for worker status

Worker crashes
^^^^^^^^^^^^^^

- Check ``logs/celery.log`` and ``logs/worker_default.log`` for error messages
- OOM kills are the most common cause — see the Model Loading section above
- The ``solo`` pool runs one task at a time; a crash during generation kills the worker process

Task timeouts
^^^^^^^^^^^^^

Large models or complex prompts may take several minutes. Check:

- The task is actually running (not stuck) via Flower
- GPU utilization — verify the GPU is active during generation
- Network issues — HuggingFace model downloads can be slow on first run

Adaptation Pipeline
-------------------

Evaluation gate loops
^^^^^^^^^^^^^^^^^^^^^

If the pipeline repeatedly fails evaluations and exhausts retries:

- Check ``evaluation_history`` on the VideoAdUnit for specific failure reasons
- Review the evaluation prompt templates — they may be too strict for the target market
- Try adjusting the evaluation templates via **Core > Prompt Templates**
- Each gate allows up to 3 retries before the pipeline stops

Schema validation errors
^^^^^^^^^^^^^^^^^^^^^^^^^

The pipeline uses structured generation (Outlines library) to constrain LLM output to Pydantic schemas. If validation fails:

- Check that the LLM model supports the required output format
- Larger models (7B) are more reliable at structured generation than smaller ones (3B)
- Check ``logs/tasks.log`` for the ``cw.lib.adaptation`` logger

Pipeline model loading errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Verify LLM models are configured and active under **Core > LLM Models**
- Check that PipelineSettings has a global default model set
- Ensure the ``PipelineModelLoader`` can find the model on HuggingFace

Docker & Infrastructure
-----------------------

Port conflicts
^^^^^^^^^^^^^^

Default ports used by the application:

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Port
     - Service
     - Fix
   * - 5435
     - PostgreSQL
     - Check for existing PostgreSQL instances
   * - 6379
     - Valkey/Redis
     - Check for existing Redis instances
   * - 8000
     - Django
     - Kill existing Django dev servers
   * - 3000
     - Grafana
     - Check for existing Grafana instances
   * - 3100
     - Loki
     - Usually no conflicts
   * - 5555
     - Flower
     - Kill existing Flower instances

Container startup order
^^^^^^^^^^^^^^^^^^^^^^^

Use ``./start.sh`` which waits for containers to be healthy before starting Django and workers. If using ``honcho start`` directly, containers may not be ready when Django starts — you'll see database connection errors that resolve after a few seconds.

Diagnostic Commands
-------------------

Quick checks for common issues:

.. code-block:: bash

   # Check all containers are running
   docker compose ps

   # Check worker status
   curl -s http://localhost:5555/api/workers | python -m json.tool

   # Check recent errors in task logs
   cat logs/tasks.log | jq 'select(.levelname == "ERROR")' | tail -20

   # Check Django is responding
   curl -s http://localhost:8000/app/ | head -5

   # Verify database connectivity
   uv run manage.py check --database default
