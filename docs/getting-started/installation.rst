Installation & Setup
====================

This guide walks you through setting up the Generative Creative Lab development environment from scratch.

Prerequisites
-------------

Before starting, make sure you have the following installed:

- **Python 3.12+** — check with ``python --version``
- **uv** — Python package manager (`installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_)
- **Docker** and **Docker Compose** — for PostgreSQL, Valkey, and the Grafana observability stack
- **Node.js** and **npm** — for Tailwind CSS compilation (check with ``node --version``)
- **Git** — for cloning the repository

Clone the Repository
--------------------

.. code-block:: bash

   git clone git@github.com:andrewmarconi/generative-creative-lab.git
   cd generative-creative-lab

Environment Configuration
-------------------------

Copy the example environment file and adjust as needed:

.. code-block:: bash

   cp .env.example .env

The defaults work for local development. The key variables:

.. list-table::
   :header-rows: 1
   :widths: 30 50 20

   * - Variable
     - Purpose
     - Default
   * - ``DJANGO_SECRET_KEY``
     - Django secret key
     - Set in example
   * - ``POSTGRES_DB`` / ``USER`` / ``PASSWORD``
     - Database credentials
     - ``cw`` / ``cw`` / ``cw_dev``
   * - ``POSTGRES_HOST`` / ``PORT``
     - Database connection
     - ``localhost`` / ``5435``
   * - ``VALKEY_HOST`` / ``PORT``
     - Celery broker (Redis-compatible)
     - ``localhost`` / ``6379``
   * - ``ANTHROPIC_API_KEY``
     - *Optional.* Enables LLM-based prompt enhancement
     -
   * - ``CIVITAI_API_KEY``
     - *Optional.* Enables auto-downloading LoRAs from CivitAI
     -

Quick Setup (Recommended)
-------------------------

The **onboarding script** automates the entire first-time setup in a single command:

.. code-block:: bash

   ./onboarding.sh

This interactive script handles everything:

1. Optionally cleans existing ``.venv`` and Docker volumes (for fresh starts)
2. Starts Docker containers (PostgreSQL 17, Valkey, Grafana/Loki stack)
3. Installs Python dependencies with ``uv sync``
4. Installs Node.js dependencies with ``npm i``
5. Runs database migrations
6. Imports all seed data:

   - Model presets (diffusion models, LoRAs)
   - Audience segments and personas
   - Reference data (regions, countries, languages, LLM models)
   - Prompt templates
   - Pipeline settings (default: Qwen 2.5 7B for all nodes)
   - Brands (if ``data/brands.json`` exists)

7. Creates an admin superuser (``admin`` / ``admin``)
8. Stops Docker containers (ready for ``./start.sh``)

Once onboarding completes, start the application:

.. code-block:: bash

   ./start.sh

Then open:

- **Django App**: http://localhost:8000/app/ (login: ``admin`` / ``admin``)
- **Grafana**: http://localhost:3000 (anonymous access enabled)
- **Flower** (task monitor): http://localhost:5555

Manual Setup
------------

If you prefer to run each step individually, or need to troubleshoot, follow the steps below.

1. Start Docker Containers
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker compose up -d --wait

This starts 5 services:

.. list-table::
   :header-rows: 1
   :widths: 20 50 15

   * - Service
     - Purpose
     - Port
   * - **PostgreSQL 17**
     - Primary database
     - 5435
   * - **Valkey**
     - Celery broker (Redis-compatible)
     - 6379
   * - **Loki**
     - Log aggregation backend
     - 3100
   * - **Alloy**
     - Log collector (ships ``logs/*.log`` to Loki)
     - —
   * - **Grafana**
     - Log search UI
     - 3000

The ``--wait`` flag blocks until health checks pass.

2. Install Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   uv sync
   npm i

``uv sync`` installs all Python packages (including PyTorch, diffusers, etc.) into a virtual environment at ``.venv/``. ``npm i`` installs Tailwind CSS for the admin UI.

3. Run Migrations
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   uv run manage.py migrate

4. Create a Superuser
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   uv run manage.py createsuperuser

Follow the prompts to set a username, email, and password.

5. Seed the Database
^^^^^^^^^^^^^^^^^^^^

Import configuration and reference data in dependency order:

.. code-block:: bash

   # Model and LoRA configuration
   uv run manage.py import_presets

   # Reference data (regions, countries, languages, LLM models)
   uv run manage.py import_reference_data

   # Prompt templates for the adaptation pipeline
   uv run manage.py import_prompt_templates

   # Audience segments and personas
   uv run manage.py import_segments
   uv run manage.py import_personas

   # Brand data (if file exists)
   uv run manage.py import_brands

.. tip::

   All import commands support ``--dry-run`` to preview changes without writing to the database.

6. Start the Application
^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended way to start all services:

.. code-block:: bash

   ./start.sh

This script:

1. Starts Docker containers (``docker compose up -d --wait``)
2. Builds Tailwind CSS (``npm run tailwind:build``)
3. Starts Django, Celery worker, Flower, and Tailwind watcher via Honcho

Alternatively, you can start processes individually:

.. code-block:: bash

   # Start Docker containers
   docker compose up -d

   # In separate terminals:
   uv run manage.py runserver                                          # Django (port 8000)
   PYTHONPATH=src uv run celery -A cw worker -Q default -E --pool=solo # Celery worker
   PYTHONPATH=src uv run celery -A cw flower --port=5555               # Flower (port 5555)

Or use Honcho to run them all (without Docker dependency ordering):

.. code-block:: bash

   uv run honcho start

Process Architecture
--------------------

The application runs as 5 concurrent processes, defined in the ``Procfile``:

.. list-table::
   :header-rows: 1
   :widths: 15 60 15

   * - Process
     - Command
     - Port
   * - **docker**
     - ``docker compose up``
     - Various
   * - **django**
     - ``uv run manage.py runserver``
     - 8000
   * - **worker**
     - Celery worker on ``default`` queue (solo pool)
     - —
   * - **flower**
     - Celery task monitor
     - 5555
   * - **tailwind**
     - Tailwind CSS watcher (rebuilds on change)
     - —

The Celery worker uses the ``solo`` pool (single-threaded) to prevent concurrent GPU model loading. This ensures one model is loaded at a time, keeping memory usage predictable.

Verifying the Setup
-------------------

Once all services are running:

1. **Django App** — Navigate to http://localhost:8000/app/ and log in. You should see the Diffusion, TV Spots, Audiences, and Core sections.

2. **Database** — Verify seed data loaded:

   - *Diffusion > Diffusion Models* should list 7+ models
   - *Core > Prompt Templates* should list 9 templates
   - *Audiences > Regions* should show geographic regions

3. **Celery** — Open Flower at http://localhost:5555 and confirm the worker is online.

4. **Grafana** — Open http://localhost:3000, navigate to *Explore > Loki*, and run the query ``{job="django"}`` to confirm log collection is working.

Optional: Pre-download Models
-----------------------------

Diffusion models are downloaded from HuggingFace on first use, which can take a while. To pre-download them:

.. code-block:: bash

   uv run manage.py preload_models

This downloads all models configured in ``data/presets.json`` to the local HuggingFace cache.

Next Steps
----------

- :doc:`first-image` — Generate your first diffusion image
- :doc:`first-adaptation` — Create your first culturally adapted TV spot
