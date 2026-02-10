Configuration
=============

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

All configuration surfaces: environment, files, and Django settings.

Planned content:

- ``.env`` variables:

  - **Required**: ``POSTGRES_*``, ``VALKEY_*``, ``DJANGO_SECRET_KEY``
  - **Optional**: ``ANTHROPIC_API_KEY``, ``CIVITAI_API_KEY``, ``MODEL_BASE_PATH``

- ``data/presets.json`` structure and per-model settings flags:

  - ``force_default_guidance``, ``enable_debug_logging``
  - ``use_sequential_cpu_offload``, ``max_sequence_length``, ``load_in_8bit``

- ``src/cw/settings.py`` key settings (Celery config, Unfold admin, logging)
- Docker Compose service ports: PostgreSQL (5435), Valkey (6379), Loki (3100), Grafana (3000)
- Celery configuration: broker, result backend, queues, time limits
