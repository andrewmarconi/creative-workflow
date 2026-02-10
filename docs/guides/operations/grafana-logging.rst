Grafana & Log Querying
======================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How to search and analyze logs using the observability stack.

Planned content:

- Access Grafana at http://localhost:3000 (anonymous login for local dev)
- Navigate to Explore → Loki data source
- Query examples:

  - ``{job="django"}`` — All Django logs
  - ``{job="celery"} | json | level="ERROR"`` — Celery errors
  - ``{job="tasks"} |= "image generation"`` — Text search

- Correlating task IDs across log files
- Filtering by log level, timestamp, and job type
- Flower task monitor at http://localhost:5555 for real-time task status
- Parsing JSON logs locally with ``jq``
