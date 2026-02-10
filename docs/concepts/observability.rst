Observability
=============

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

Logging, monitoring, and debugging the system.

Planned content:

- Logging architecture: 5 JSON log files (tasks, worker_default, worker_enhancement, django, celery)
- Log pipeline: log files → Alloy collector → Loki → Grafana
- Grafana dashboard at http://localhost:3000
- Flower task monitor at http://localhost:5555
- Structured JSON logs and querying with ``jq``
- How to debug a failed job: correlating task IDs across logs
- Docker Compose observability services (Loki, Alloy, Grafana)
