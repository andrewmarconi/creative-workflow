Architecture Overview
=====================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How the system fits together: processes, apps, and data flow.

Planned content:

- Process model: Docker, Django, Celery worker, Flower (4 concurrent processes via Honcho)
- ``src`` layout and Django app map (core, diffusion, tvspots, audiences)
- Supporting library modules (``cw.lib/``)
- Data flow diagrams (Mermaid): admin → Celery → worker → model → media
- Database architecture (PostgreSQL) and broker (Valkey/Redis)
- Configuration layers: ``.env``, ``presets.json``, Django settings, database
