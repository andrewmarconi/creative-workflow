Management Commands
===================

Complete reference for all Django management commands, organized by app.

All commands are run with ``uv run manage.py <command>``.

Diffusion
---------

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Synopsis
     - Key Flags
   * - ``import_presets``
     - Sync ``data/presets.json`` to database (models and LoRAs). Uses ``update_or_create()`` keyed on slug/path.
     - ``--file PATH`` (default ``data/presets.json``), ``--clear`` (wipe before import)
   * - ``export_presets``
     - Export DiffusionModel and LoraModel records to JSON.
     - ``--file PATH`` (default ``data/presets.json``), ``--active-only``
   * - ``import_prompts``
     - Bulk-import prompts from JSON or plain-text file.
     - ``--file PATH`` (required), ``--style {auto,photography,artistic,realistic,cinematic,coloring-book}``, ``--clear``, ``--skip-duplicates``
   * - ``export_prompts``
     - Export Prompt records to JSON.
     - ``--file PATH`` (default ``data/prompts.json``), ``--enhanced-only``
   * - ``import_adaptations``
     - Import ``adaptations.json`` into Prompt + DiffusionJob records.
     - ``--file PATH`` (default ``data/adaptations.json``), ``--dry-run``
   * - ``preload_models``
     - Pre-download HuggingFace models to local cache.
     - ``--model SLUG`` (single model), ``--list`` (show available)

Core
----

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Synopsis
     - Key Flags
   * - ``import_reference_data``
     - Import regions, countries, languages, and LLM models from ``data/``. Processes files in dependency order.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_reference_data``
     - Export reference data to six separate JSON files.
     - ``--dir DIR`` (default ``data``)
   * - ``import_prompt_templates``
     - Import Jinja2 prompt templates from JSON. Auto-increments version on content changes.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_prompt_templates``
     - Export active PromptTemplate records to JSON.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_coredata``
     - Export combined LLM models and languages to a single JSON file (legacy).
     - ``--file PATH`` (default ``data/core_data.json``), ``--models-only``, ``--languages-only``, ``--active-only``

Audiences
---------

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Synopsis
     - Key Flags
   * - ``import_segments``
     - Import audience segments from JSON. Keyed on ``(category, vector, value)`` composite.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_segments``
     - Export Segment records to ``segments.json``.
     - ``--dir DIR`` (default ``data``)
   * - ``import_personas``
     - Import personas and segment mappings from two JSON files. Resolves geographic FKs by code.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_personas``
     - Export Persona records to ``personas.json`` and ``persona_segments.json``.
     - ``--dir DIR`` (default ``data``)

TV Spots
--------

.. list-table::
   :header-rows: 1
   :widths: 25 40 35

   * - Command
     - Synopsis
     - Key Flags
   * - ``import_brands``
     - Import brand records from JSON. Keyed on ``code``.
     - ``--dir DIR`` (default ``data``), ``--dry-run``
   * - ``export_brands``
     - Export Brand records to ``brands.json``.
     - ``--dir DIR`` (default ``data``)
   * - ``import_tvspot``
     - Import a TV spot from a JSON file. Creates Campaign + origin VideoAdUnit + script rows.
     - ``file`` (positional, required), ``--dry-run``
   * - ``import_markets``
     - Import adaptation markets from ``market_profiles.json``.
     - ``--file PATH`` (default ``data/market_profiles.json``), ``--dry-run``
   * - ``export_markets``
     - Export adaptation markets to ``market_profiles.json``.
     - ``--file PATH`` (default ``data/market_profiles.json``)

Common Flags
------------

``--dry-run``
^^^^^^^^^^^^^

Preview what would change without writing to the database. Supported by most import commands:

.. code-block:: bash

   uv run manage.py import_reference_data --dry-run
   uv run manage.py import_prompt_templates --dry-run
   uv run manage.py import_segments --dry-run
   uv run manage.py import_personas --dry-run
   uv run manage.py import_brands --dry-run
   uv run manage.py import_tvspot data/spot.json --dry-run
   uv run manage.py import_adaptations --dry-run

``--dir``
^^^^^^^^^

Override the default ``data/`` directory for file I/O. Supported by reference data, audiences, brands, and prompt template commands:

.. code-block:: bash

   uv run manage.py export_reference_data --dir backups/2026-02/
   uv run manage.py import_reference_data --dir backups/2026-02/
   uv run manage.py export_segments --dir backups/2026-02/

``--file``
^^^^^^^^^^

Override the exact file path (instead of directory). Used by preset, prompt, and market commands:

.. code-block:: bash

   uv run manage.py import_presets --file custom/presets.json
   uv run manage.py export_prompts --file output/prompts.json

Import Dependency Order
-----------------------

When populating a new environment, import data in this sequence:

.. code-block:: bash

   # 1. Core reference data (handles internal dependencies)
   uv run manage.py import_reference_data

   # 2. Prompt templates
   uv run manage.py import_prompt_templates

   # 3. Diffusion presets (models and LoRAs)
   uv run manage.py import_presets

   # 4. Audience segments
   uv run manage.py import_segments

   # 5. Personas (depends on segments + reference data)
   uv run manage.py import_personas

   # 6. Brands
   uv run manage.py import_brands

   # 7. TV spots (depends on reference data for language lookup)
   uv run manage.py import_tvspot data/example_tvspot.json

The ``import_reference_data`` command processes its own internal dependencies: LLM Models, Regions, Languages, Countries, then M2M mappings.

Idempotency
-----------

All import commands use ``update_or_create()`` and are safe to run repeatedly. Natural keys used for matching:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Model
     - Natural Key
   * - DiffusionModel
     - ``slug``
   * - LoraModel
     - ``path`` or ``air`` (CivitAI URN)
   * - PromptTemplate
     - ``slug``
   * - Region / Country / Language
     - ``code``
   * - LLMModel
     - ``model_id``
   * - Segment
     - ``(category, vector, value)``
   * - Persona
     - ``name``
   * - Brand
     - ``code``
