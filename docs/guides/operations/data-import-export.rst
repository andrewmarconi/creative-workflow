Data Import & Export
====================

This guide covers all management commands for importing and exporting data across the application.

Command Overview
----------------

Commands are organized by domain. All import commands support ``--dry-run`` for previewing changes. Most export commands support ``--dir`` for custom output paths.

Diffusion
^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``import_presets``
     - Sync ``data/presets.json`` to database (models and LoRAs)
   * - ``export_presets``
     - Export models and LoRAs from database to JSON
   * - ``import_prompts``
     - Bulk import diffusion prompts
   * - ``export_prompts``
     - Export prompts to file
   * - ``preload_models``
     - Pre-download models to HuggingFace cache

Core
^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``import_prompt_templates``
     - Import LLM prompt templates from ``data/prompt_templates.json``
   * - ``export_prompt_templates``
     - Export active templates to JSON
   * - ``import_reference_data``
     - Import regions, countries, languages, LLM models from ``data/``
   * - ``export_reference_data``
     - Export reference data to separate JSON files

Audiences
^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``import_segments``
     - Import audience segments from ``data/segments.json``
   * - ``export_segments``
     - Export segments to JSON
   * - ``import_personas``
     - Import personas from ``data/personas.json``
   * - ``export_personas``
     - Export personas and persona-segment mappings

TV Spots
^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Description
   * - ``import_brands``
     - Import brand data from ``data/brands.json``
   * - ``export_brands``
     - Export brands to JSON
   * - ``import_tvspot``
     - Import a TV spot from a JSON file (creates Campaign + origin VideoAdUnit)
   * - ``import_adaptations``
     - Import adaptations JSON into prompts and jobs

Import Dependency Order
-----------------------

When setting up a new environment, import data in this order:

.. code-block:: bash

   # 1. Core reference data (dependency-ordered internally)
   uv run manage.py import_reference_data

   # 2. Prompt templates
   uv run manage.py import_prompt_templates

   # 3. Diffusion presets (models and LoRAs)
   uv run manage.py import_presets

   # 4. Audience segments (no dependencies)
   uv run manage.py import_segments

   # 5. Personas (depends on segments + reference data)
   uv run manage.py import_personas

   # 6. Brands (no dependencies)
   uv run manage.py import_brands

   # 7. TV spots (depends on reference data for language lookup)
   uv run manage.py import_tvspot data/example_tvspot.json

The ``import_reference_data`` command handles its own internal dependencies: LLM Models → Regions → Countries → Languages → M2M mappings.

Common Options
--------------

``--dry-run``
^^^^^^^^^^^^^

Preview what would change without creating or modifying records:

.. code-block:: bash

   uv run manage.py import_reference_data --dry-run
   uv run manage.py import_prompt_templates --dry-run
   uv run manage.py import_segments --dry-run
   uv run manage.py import_personas --dry-run
   uv run manage.py import_brands --dry-run
   uv run manage.py import_tvspot data/spot.json --dry-run

``--dir``
^^^^^^^^^

Export to or import from a custom directory (instead of the default ``data/``):

.. code-block:: bash

   uv run manage.py export_reference_data --dir backups/2024-02/
   uv run manage.py export_prompt_templates --dir backups/2024-02/
   uv run manage.py export_segments --dir backups/2024-02/
   uv run manage.py export_personas --dir backups/2024-02/
   uv run manage.py export_brands --dir backups/2024-02/

Data Files
----------

All configuration files live under ``data/``:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - Contents
   * - ``presets.json``
     - Diffusion models and LoRA configurations
   * - ``prompt_templates.json``
     - LLM prompt templates (Jinja2)
   * - ``llm_models.json``
     - LLM model configurations
   * - ``regions.json``
     - Geographic regions
   * - ``countries.json``
     - Countries with default language references
   * - ``languages.json``
     - Languages with primary LLM model references
   * - ``country_regions.json``
     - Country-to-Region M2M mappings
   * - ``country_languages.json``
     - Country-to-Language M2M mappings
   * - ``segments.json``
     - Audience segments (demographic, behavioral, psychographic)
   * - ``personas.json``
     - Persona records with geographic references
   * - ``persona_segments.json``
     - Persona-to-Segment M2M mappings
   * - ``brands.json``
     - Brand reference data
   * - ``example_tvspot.json``
     - Example TV spot JSON for testing imports

Backup & Restore
-----------------

To create a complete backup:

.. code-block:: bash

   mkdir -p backups/$(date +%Y-%m-%d)
   uv run manage.py export_presets
   uv run manage.py export_prompt_templates --dir backups/$(date +%Y-%m-%d)/
   uv run manage.py export_reference_data --dir backups/$(date +%Y-%m-%d)/
   uv run manage.py export_segments --dir backups/$(date +%Y-%m-%d)/
   uv run manage.py export_personas --dir backups/$(date +%Y-%m-%d)/
   uv run manage.py export_brands --dir backups/$(date +%Y-%m-%d)/

To restore from backup, import in dependency order using the ``--dir`` option where supported.
