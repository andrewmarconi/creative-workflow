Quick Start
===========

Get up and running with Generative Creative Lab in minutes.

Prerequisites
-------------

- Python 3.12+ (managed via ``uv``)
- Docker and Docker Compose (for PostgreSQL and Valkey)
- GPU: Apple Silicon (MPS) or NVIDIA (CUDA)
- ~15-30GB storage for model cache

Installation
------------

1. **Clone the repository**::

    git clone https://github.com/andrewmarconi/generative-creative-lab.git
    cd generative-creative-lab

2. **Install dependencies**::

    uv sync

3. **Configure environment**::

    cp .env.example .env
    # Edit .env with your settings (see Configuration below)

4. **Authenticate with HuggingFace** (required for Hub models)::

    huggingface-cli login

5. **Start all services**::

    ./start.sh
    # Or: uv run honcho start

6. **Initialize database** (in a new terminal)::

    uv run manage.py migrate
    uv run manage.py createsuperuser
    uv run manage.py import_presets

7. **Access the admin UI** at http://localhost:8000/admin/

Service Architecture
--------------------

The ``start.sh`` script (or ``honcho start``) launches four processes:

.. list-table::
   :header-rows: 1
   :widths: 15 50

   * - Process
     - Function
   * - **docker**
     - Data persistence (PostgreSQL + Valkey) and observability (Grafana/Loki)
   * - **django**
     - Creative studio interface at http://localhost:8000/admin/
   * - **worker**
     - Image generation execution (``default`` queue)
   * - **enhancement**
     - Prompt transformation via local LLM (``enhancement`` queue)

For minimal setup (configuration only, no generation)::

    uv run honcho start docker django

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

Environment variables in ``.env``:

**Required**

- ``POSTGRES_*`` - Database connection (defaults work with Docker Compose)
- ``VALKEY_*`` - Redis/Valkey broker connection
- ``DJANGO_SECRET_KEY`` - Django secret key

**Optional**

- ``CIVITAI_API_KEY`` - Enable auto-downloading LoRA models from CivitAI
- ``ANTHROPIC_API_KEY`` - Enable LLM-powered prompt enhancement
- ``MODEL_BASE_PATH`` - Base directory for local ``.safetensors`` files

Common Commands
---------------

**Development**::

    ./start.sh                          # Start all services
    uv run honcho start docker django   # Minimal setup (no workers)

**Database & Configuration**::

    uv run manage.py migrate            # Run database migrations
    uv run manage.py import_presets     # Sync model configurations
    uv run manage.py preload_models     # Pre-download models to cache
    uv run manage.py createsuperuser    # Create admin user

**Content Management**::

    uv run manage.py import_prompts     # Bulk import prompts
    uv run manage.py export_prompts     # Export prompts to file

Next Steps
----------

- :doc:`guides/model-reference` - Learn about available models and their characteristics
- :doc:`guides/adding-models` - Extend the framework with new models
- :doc:`troubleshooting` - Common issues and solutions
- :doc:`/developer/architecture` - Deep dive into system architecture
