Quick Start
===========

Getting Started
---------------

1. **Install dependencies**::

    uv sync

2. **Start all services** (PostgreSQL, Valkey, Django, Celery workers)::

    honcho start

3. **Create a superuser**::

    uv run manage.py createsuperuser

4. **Import model presets**::

    uv run manage.py import_presets

5. **Access the admin UI** at http://localhost:8000/admin/

Creating Your First Image
-------------------------

1. Navigate to **Diffusion > Prompts** in the admin
2. Click **Add Prompt**
3. Enter a text prompt (e.g., "a beautiful sunset over mountains")
4. Select a model (e.g., "Z-Image Turbo" for fast generation)
5. Save the prompt
6. Navigate to **Diffusion > Jobs**
7. Create a new job linked to your prompt
8. The job will automatically queue for processing
9. Refresh to see the generated images

Configuration
-------------

Environment variables (set in ``.env``):

- ``POSTGRES_*`` - Database connection
- ``VALKEY_*`` - Redis/Valkey broker connection
- ``CIVITAI_API_KEY`` - For auto-downloading LoRA models
- ``ANTHROPIC_API_KEY`` - For LLM prompt enhancement
- ``MODEL_BASE_PATH`` - Base directory for local model files

See ``CLAUDE.md`` for full documentation.
