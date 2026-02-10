Observability
=============

This page explains the logging architecture, the Grafana/Loki stack, Flower task monitoring, and how to debug failed jobs.

Logging Architecture
--------------------

All application logs are written as **structured JSON** to rotating files in the ``logs/`` directory. The log pipeline has three stages:

.. mermaid::

   graph LR
       Django[Django / Celery / Tasks] -->|write| Logs["logs/*.log<br/>(JSON)"]
       Logs -->|collect| Alloy[Alloy]
       Alloy -->|ship| Loki[Loki<br/>:3100]
       Loki -->|query| Grafana[Grafana<br/>:3000]

1. **Application writes** — Python loggers write structured JSON to rotating log files
2. **Alloy collects** — Grafana Alloy watches the log files and ships entries to Loki
3. **Loki stores** — Loki indexes and stores logs for querying
4. **Grafana displays** — Grafana provides a web UI for searching and filtering logs

Log Files
^^^^^^^^^

Four log files, each capturing a different concern:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - File
     - Contents
   * - ``logs/django.log``
     - Django server logs (requests, middleware, ORM)
   * - ``logs/celery.log``
     - Celery framework logs (worker lifecycle, task routing, connection events)
   * - ``logs/tasks.log``
     - Task execution logs — diffusion generation, adaptation pipeline, prompt enhancement, storyboard generation, model loading, CivitAI downloads
   * - ``logs/worker_*.log``
     - Per-worker logs (``worker_default.log``, ``worker_enhancement.log``)

All files use ``RotatingFileHandler`` with a 10 MB limit and 5 backup files.

JSON Format
^^^^^^^^^^^

Every log entry is a JSON object produced by ``pythonjsonlogger``:

.. code-block:: json

   {
     "asctime": "2026-02-10 14:23:45,123",
     "name": "cw.lib.models",
     "levelname": "INFO",
     "message": "Pipeline loaded successfully: Flux.1-dev on CUDA",
     "pathname": "src/cw/lib/models/base.py",
     "lineno": 177
   }

Loggers
^^^^^^^

The application defines targeted loggers for each subsystem:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Logger
     - Level
     - Purpose
   * - ``django``
     - INFO
     - Django server
   * - ``celery``
     - INFO
     - Celery framework
   * - ``cw.diffusion.tasks``
     - INFO
     - Diffusion job execution
   * - ``cw.tvspots.tasks``
     - INFO
     - TV spot adaptation tasks
   * - ``cw.lib.models``
     - DEBUG
     - Diffusion model loading and generation
   * - ``cw.lib.adaptation``
     - DEBUG
     - Adaptation pipeline execution
   * - ``cw.lib.prompt_enhancer``
     - DEBUG
     - Prompt enhancement
   * - ``cw.lib.storyboard``
     - DEBUG
     - Storyboard generation
   * - ``cw.lib.civitai``
     - DEBUG
     - CivitAI LoRA downloads
   * - ``cw.lib.security``
     - INFO
     - File upload validation

Library-level loggers (``cw.lib.*``) are set to DEBUG to capture detailed execution traces, while task and framework loggers use INFO to reduce noise.

Grafana + Loki
--------------

The observability stack runs as three Docker Compose services, always started alongside the application.

**Loki** (port 3100)
   Log aggregation backend. Receives log entries from Alloy, indexes them, and stores them on disk. Configuration uses Loki's default ``local-config.yaml``.

**Alloy**
   Grafana's unified observability collector (replaces Promtail). Watches the ``logs/`` directory and ships entries to Loki.

   Alloy is configured in ``alloy-config.alloy`` with four source targets:

   .. list-table::
      :header-rows: 1
      :widths: 20 30 50

      * - Job Label
        - Source
        - Files
      * - ``django``
        - ``logs/django.log``
        - Django server logs
      * - ``celery``
        - ``logs/celery.log``
        - Celery framework logs
      * - ``tasks``
        - ``logs/tasks.log``
        - Task execution logs
      * - ``workers``
        - ``logs/worker_*.log``
        - Per-worker logs (glob pattern)

   Alloy's JSON processing pipeline extracts ``level``, ``logger``, ``message``, and ``timestamp`` from each JSON entry and adds them as Loki labels for efficient querying.

**Grafana** (port 3000)
   Web UI for log search and visualization. Anonymous login is enabled for local development (with admin role), so no credentials are needed.

   Loki is auto-provisioned as the default datasource via ``grafana/provisioning/datasources/loki.yml``.

Querying Logs
^^^^^^^^^^^^^

In Grafana, navigate to **Explore** and select the **Loki** datasource. LogQL query examples:

.. code-block:: text

   # All Django logs
   {job="django"}

   # Celery errors only
   {job="celery"} | json | level="ERROR"

   # Search for text in task logs
   {job="tasks"} |= "image generation"

   # Filter by logger name
   {job="tasks"} | json | logger="cw.lib.models"

   # All errors across all jobs
   {level="ERROR"}

   # Worker logs
   {job="workers"}

Local Log Analysis
^^^^^^^^^^^^^^^^^^

For quick analysis without Grafana, use ``jq`` to parse JSON logs directly:

.. code-block:: bash

   # Stream task logs
   tail -f logs/tasks.log

   # Filter errors
   cat logs/tasks.log | jq 'select(.levelname == "ERROR")'

   # Filter by logger
   cat logs/tasks.log | jq 'select(.name == "cw.lib.models")'

   # Search message text
   cat logs/tasks.log | jq 'select(.message | contains("LoRA"))'

Flower Task Monitor
-------------------

`Flower <https://flower.readthedocs.io/>`_ runs on port 5555 and provides real-time visibility into Celery task execution:

- **Active tasks** — currently executing tasks with worker assignment
- **Completed tasks** — recent results with timing and status
- **Queued tasks** — tasks waiting in the broker
- **Worker status** — worker heartbeat, active task count, resource usage

Access Flower at http://localhost:5555 when the application is running.

Debugging a Failed Job
----------------------

When a DiffusionJob or adaptation fails, follow this sequence:

1. **Check the job status** in the Django admin. The detail page shows the current status and, for adaptations, the ``evaluation_history`` and ``error_message`` fields.

2. **Check Flower** for the task result. Find the task by its ID (shown on the job detail page) to see the exception traceback and timing.

3. **Search task logs** for the job ID:

   .. code-block:: bash

      cat logs/tasks.log | jq 'select(.message | contains("JOB_ID"))'

   Or in Grafana:

   .. code-block:: text

      {job="tasks"} |= "JOB_ID"

4. **Check model loading** — if the error is a model load failure, filter for the model logger:

   .. code-block:: bash

      cat logs/tasks.log | jq 'select(.name == "cw.lib.models" and .levelname == "ERROR")'

5. **Check for OOM errors** — out-of-memory errors during generation typically appear as CUDA or MPS errors in the task logs. The warm cache (see :doc:`diffusion-models`) ensures only one model is loaded at a time, but large models can still exceed available VRAM.

6. **For adaptation failures** — check the VideoAdUnit's ``evaluation_history`` to see which gate failed and how many revisions were attempted. The ``pipeline_metadata`` field records the final model ID and revision counts.
