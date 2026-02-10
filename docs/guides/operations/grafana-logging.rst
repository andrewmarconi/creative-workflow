Grafana & Log Querying
======================

This guide covers searching and analyzing logs using the Grafana/Loki observability stack and local tools.

Accessing Grafana
-----------------

Grafana runs on **port 3000** as part of the Docker Compose stack. It starts automatically with the application.

1. Open http://localhost:3000
2. Anonymous login is enabled for local development (no credentials needed)
3. Navigate to **Explore** in the left sidebar
4. Select the **Loki** data source (auto-provisioned)

LogQL Query Examples
--------------------

Basic Queries
^^^^^^^^^^^^^

.. code-block:: text

   # All Django server logs
   {job="django"}

   # All Celery framework logs
   {job="celery"}

   # All task execution logs
   {job="tasks"}

   # All worker logs (glob pattern)
   {job="workers"}

Filtering by Level
^^^^^^^^^^^^^^^^^^

.. code-block:: text

   # Celery errors only
   {job="celery"} | json | level="ERROR"

   # All errors across all jobs
   {job="tasks"} | json | level="ERROR"

   # Warnings and above
   {job="tasks"} | json | level=~"WARNING|ERROR|CRITICAL"

Text Search
^^^^^^^^^^^

.. code-block:: text

   # Search for text in task logs
   {job="tasks"} |= "image generation"

   # Search for a specific model
   {job="tasks"} |= "Flux.1-dev"

   # Search for LoRA-related messages
   {job="tasks"} |= "LoRA"

Filtering by Logger
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   # Diffusion model loading and generation
   {job="tasks"} | json | logger="cw.lib.models"

   # Adaptation pipeline execution
   {job="tasks"} | json | logger="cw.lib.adaptation"

   # Prompt enhancement
   {job="tasks"} | json | logger="cw.lib.prompt_enhancer"

   # CivitAI LoRA downloads
   {job="tasks"} | json | logger="cw.lib.civitai"

   # File upload validation
   {job="tasks"} | json | logger="cw.lib.security"

Correlating Task IDs
^^^^^^^^^^^^^^^^^^^^

To trace a specific task across logs:

.. code-block:: text

   # Search for a specific job ID
   {job="tasks"} |= "JOB_ID_HERE"

   # Search for a Celery task ID
   {job="tasks"} |= "task-uuid-here"

   # Search for a specific ad unit ID
   {job="tasks"} |= "video_ad_unit_id"

Flower Task Monitor
-------------------

**Flower** runs on **port 5555** and provides real-time visibility into Celery tasks:

- **Active tasks** — currently executing tasks with worker assignment
- **Completed tasks** — recent results with timing and status
- **Queued tasks** — tasks waiting in the broker
- **Worker status** — heartbeat, active task count, resource usage

Access Flower at http://localhost:5555.

Useful views:

- **Tasks** tab — find tasks by name, state, or ID
- **Worker** tab — check worker health and concurrency
- **Broker** tab — view queue depths

Local Log Analysis
------------------

For quick analysis without Grafana, parse the JSON log files directly with ``jq``:

Streaming Logs
^^^^^^^^^^^^^^

.. code-block:: bash

   # Stream task logs in real time
   tail -f logs/tasks.log

   # Stream with JSON pretty-printing
   tail -f logs/tasks.log | jq .

Filtering by Level
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # All errors
   cat logs/tasks.log | jq 'select(.levelname == "ERROR")'

   # Warnings and errors
   cat logs/tasks.log | jq 'select(.levelname == "ERROR" or .levelname == "WARNING")'

Filtering by Logger
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Diffusion model logs only
   cat logs/tasks.log | jq 'select(.name == "cw.lib.models")'

   # Pipeline logs only
   cat logs/tasks.log | jq 'select(.name == "cw.lib.adaptation")'

Text Search
^^^^^^^^^^^

.. code-block:: bash

   # Search message text
   cat logs/tasks.log | jq 'select(.message | contains("LoRA"))'

   # Search for a job ID
   cat logs/tasks.log | jq 'select(.message | contains("ACME-2024-001"))'

Log Files
---------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Contents
   * - ``logs/django.log``
     - Django server logs (requests, middleware, ORM)
   * - ``logs/celery.log``
     - Celery framework logs (worker lifecycle, task routing)
   * - ``logs/tasks.log``
     - Task execution logs (diffusion, adaptation, enhancement, storyboard)
   * - ``logs/worker_default.log``
     - Default worker logs
   * - ``logs/worker_enhancement.log``
     - Enhancement worker logs

All files use ``RotatingFileHandler`` with a 10 MB limit and 5 backup files. See :doc:`/concepts/observability` for the full logging architecture.
