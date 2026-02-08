JSON Data Schemas
=================

JSON Schema definitions for the data files used by Generative Creative Lab. All schemas
use `JSON Schema draft 2020-12 <https://json-schema.org/draft/2020-12/schema>`_.

These files are used for moving information into or out of the platform.

----

Presets Schema
--------------

Defines the configuration for diffusion models and LoRA adapters.

:Data File: :download:`presets.json <../../data/presets.json>`

Structure
~~~~~~~~~

The presets file contains two top-level arrays:

**models**
   Available diffusion models with their pipeline configurations and inference settings.

**loras**
   LoRA adapters with CivitAI AIR URNs for auto-download and recommended settings.

Model Properties
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``slug``
     - string
     - Unique identifier (lowercase, underscores only)
   * - ``label``
     - string
     - Human-readable display name
   * - ``path``
     - string
     - HuggingFace model path or local ``.safetensors`` path
   * - ``pipeline``
     - string
     - Diffusers pipeline class name
   * - ``base_architecture``
     - string
     - Base model architecture: ``sd15``, ``sdxl``, ``flux1``, ``qwen``, ``zimage``
   * - ``settings``
     - object
     - Inference settings (steps, guidance, dimensions, etc.)

LoRA Properties
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``label``
     - string
     - Human-readable display name
   * - ``base_architecture``
     - string
     - Compatible base model architecture
   * - ``theme``
     - string
     - Visual style category for filtering
   * - ``air``
     - string
     - CivitAI AIR URN for auto-download
   * - ``prompt``
     - string
     - Trigger words to append when using this LoRA
   * - ``negative_prompt``
     - string
     - Recommended negative prompt
   * - ``settings.strength``
     - number
     - LoRA weight multiplier (0-2)

Example
~~~~~~~

.. code-block:: json

   {
     "models": [
       {
         "slug": "flux1_dev",
         "label": "Flux.1 Dev",
         "path": "black-forest-labs/FLUX.1-dev",
         "pipeline": "FluxPipeline",
         "base_architecture": "flux1",
         "settings": {
           "steps": 28,
           "guidance_scale": 3.5,
           "default_width": 1024,
           "default_height": 1024,
           "max_pixels": 2097152,
           "dtype": "bfloat16",
           "supports_negative_prompt": false,
           "scheduler": "FlowMatchEulerDiscreteScheduler",
           "max_sequence_length": 512,
           "token_window": 512,
           "vram_usage": 24576
         }
       }
     ],
     "loras": [
       {
         "label": "Pen & Ink Illustration",
         "base_architecture": "zimage",
         "theme": "illustration",
         "settings": {
           "strength": 0.7,
           "guidance_scale": 1.0
         },
         "air": "urn:air:zimageturbo:lora:civitai:2344335@2636956",
         "prompt": "phrsink, pen and ink illustration"
       }
     ]
   }

----

TV Spot Schema
--------------

Defines the format for television commercial scripts used in adaptation workflows.

:Data File: :download:`example_tvspot.json <../../data/example_tvspot.json>`

Structure
~~~~~~~~~

A TV spot script contains metadata about the commercial and a sequential array of shots.

Top-Level Properties
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``client_name``
     - string
     - Name of the client or company
   * - ``brand_name``
     - string
     - Product or brand featured in the spot
   * - ``script_title``
     - string
     - Title with duration indicator (e.g., "Morning Boost 30s")
   * - ``total_runtime_seconds``
     - number
     - Total duration in seconds
   * - ``job_id``
     - string
     - Internal project identifier
   * - ``language``
     - string
     - BCP 47 language code (e.g., ``en-US``, ``es-MX``)
   * - ``notes``
     - string
     - Additional production notes
   * - ``script_rows``
     - array
     - Sequential shots/scenes

Script Row Properties
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``shot_number``
     - string
     - Two-digit shot identifier (e.g., ``"01"``)
   * - ``timecode_start``
     - string
     - Start timecode in ``HH:MM:SS:FF`` format
   * - ``duration_seconds``
     - number
     - Duration of the shot in seconds
   * - ``visual_text``
     - string
     - Visual description: shot type, action, talent, supers, legal
   * - ``audio_text``
     - string
     - Audio elements: VO, SFX, music direction

Example
~~~~~~~

.. code-block:: json

   {
     "client_name": "Acme Corporation",
     "brand_name": "Acme Energy Drink",
     "script_title": "Morning Boost 30s",
     "total_runtime_seconds": 30,
     "job_id": "ACME-2024-001",
     "language": "en-US",
     "script_rows": [
       {
         "shot_number": "01",
         "timecode_start": "00:00:00:00",
         "duration_seconds": 3.0,
         "visual_text": "Wide shot: Urban apartment, early morning...",
         "audio_text": "SFX: Alarm buzzing\nMUSIC: Soft, building instrumental"
       }
     ]
   }

----

Reference Data Schemas
----------------------

Reference data for regions, countries, languages, and LLM models is stored in separate
JSON files under ``data/``. These files are imported via the ``import_reference_data``
management command and exported via ``export_reference_data``.

Data Files
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Description
   * - :download:`regions.json <../../data/regions.json>`
     - Geographic/cultural regions (e.g., DACH, NORDICS, LATAM)
   * - :download:`countries.json <../../data/countries.json>`
     - Countries with default language references
   * - :download:`languages.json <../../data/languages.json>`
     - Languages with primary LLM model references
   * - :download:`llm_models.json <../../data/llm_models.json>`
     - LLM models for text generation in adaptation tasks
   * - :download:`country_regions.json <../../data/country_regions.json>`
     - Many-to-many: Country to Region mappings
   * - :download:`country_languages.json <../../data/country_languages.json>`
     - Many-to-many: Country to Language mappings (with ``is_primary`` flag)

Relationship Handling
~~~~~~~~~~~~~~~~~~~~~

References between files use codes or model IDs rather than database PKs:

- ``languages.json`` references ``primary_model`` by ``model_id`` (e.g., ``"Qwen/Qwen2.5-7B-Instruct"``)
- ``countries.json`` references ``default_language`` by language ``code`` (e.g., ``"en-US"``)
- M2M files use ``country_code``, ``region_code``, ``language_code`` for references

Import Dependency Order
~~~~~~~~~~~~~~~~~~~~~~~

The ``import_reference_data`` command imports files in dependency order:

1. LLM Models (no dependencies)
2. Regions (no dependencies)
3. Countries (optional FK to Language, resolved after Languages import)
4. Languages (FK to LLM Model for ``primary_model``)
5. Country-Region mappings (FKs to Country, Region)
6. Country-Language mappings (FKs to Country, Language)

See :doc:`/research/AdaptationProfiles` for the cultural adaptation research framework that
informed the design of this reference data system.

----

Segmentation Schemas
--------------------

Non-geographic audience segmentation data (demographic, behavioral, psychographic) is stored in
separate JSON files under ``data/``. These files are imported via the ``import_segments`` and
``import_personas`` management commands.

Data Files
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Description
   * - :download:`segments.json <../../data/segments.json>`
     - Demographic, behavioral, and psychographic audience segments
   * - ``personas.json``
     - Named collections of segments representing target audience profiles
   * - ``persona_segments.json``
     - Many-to-many: Persona to Segment mappings (with display order)

Segments Schema
~~~~~~~~~~~~~~~

**Schema File**: ``data/schemas/segments.schema.json``

Each segment represents a position along a specific dimension of audience analysis. Segments are
organized into three categories: DEMOGRAPHIC, BEHAVIORAL, and PSYCHOGRAPHIC.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``category``
     - string (enum)
     - Segment category: ``DEMOGRAPHIC``, ``BEHAVIORAL``, or ``PSYCHOGRAPHIC``
   * - ``vector``
     - string (1-100 chars)
     - Dimension being segmented (e.g., "Household Income", "Usage Rate")
   * - ``value``
     - string (1-100 chars)
     - Position on the dimension (e.g., "$75K-$100K", "Heavy User")
   * - ``description``
     - string (optional)
     - Longer segment description
   * - ``insights``
     - array (optional)
     - Structured insights with headings and points
   * - ``is_active``
     - boolean
     - Whether the segment is currently active

**Example**:

.. code-block:: json

   [
     {
       "category": "DEMOGRAPHIC",
       "vector": "Age",
       "value": "25-34 (Millennials - Younger)",
       "description": "",
       "insights": [],
       "is_active": true
     },
     {
       "category": "BEHAVIORAL",
       "vector": "Innovation Adoption",
       "value": "Early Adopters (13.5%)",
       "description": "Respect, opinion leaders, educated, socially forward",
       "insights": [
         {
           "heading": "Characteristics",
           "points": [
             "Willing to try new products before most others",
             "Often serve as opinion leaders in their communities",
             "Generally higher education and income levels"
           ]
         }
       ],
       "is_active": true
     }
   ]

Personas Schema
~~~~~~~~~~~~~~~

**Schema File**: ``data/schemas/personas.schema.json``

Personas combine geographic segments (Region/Country/Language) with non-geographic segments
to create complete target audience profiles.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``name``
     - string (1-200 chars)
     - Persona name (e.g., "Budget-Conscious First-Timer")
   * - ``description``
     - string (optional)
     - Detailed persona description
   * - ``region_code``
     - string | null
     - Region code (e.g., "NA", "DACH") - must match existing Region.code
   * - ``country_code``
     - string | null
     - ISO 3166-1 alpha-2 code (e.g., "US", "DE") - must match existing Country.code
   * - ``language_code``
     - string | null
     - Locale code (e.g., "en-US", "de-CH") - must match existing Language.code
   * - ``is_active``
     - boolean
     - Whether the persona is currently active

**Code Validation Patterns**:

- ``region_code``: ``^[A-Z_]+$`` (uppercase letters and underscores)
- ``country_code``: ``^[A-Z]{2}$`` (ISO 3166-1 alpha-2 format)
- ``language_code``: ``^[a-z]{2}-[A-Z]{2}$`` (language-country format)

**Example**:

.. code-block:: json

   [
     {
       "name": "Urban Tech-Savvy Millennial",
       "description": "Young professional in urban area, early adopter of technology",
       "region_code": "NA",
       "country_code": "US",
       "language_code": "en-US",
       "is_active": true
     },
     {
       "name": "Budget-Conscious Student",
       "description": "Cost-sensitive younger demographic focused on value",
       "region_code": null,
       "country_code": null,
       "language_code": null,
       "is_active": true
     }
   ]

Persona-Segment Mappings Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Schema File**: ``data/schemas/persona_segments.schema.json``

Defines the many-to-many relationships between personas and non-geographic segments.

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``persona_name``
     - string (1-200 chars)
     - Name of persona - must match existing Persona.name
   * - ``segment_category``
     - string (enum)
     - ``DEMOGRAPHIC``, ``BEHAVIORAL``, or ``PSYCHOGRAPHIC``
   * - ``segment_vector``
     - string (1-100 chars)
     - Must match existing Segment.vector
   * - ``segment_value``
     - string (1-100 chars)
     - Must match existing Segment.value
   * - ``order_index``
     - integer (≥ 0)
     - Display order within the persona (lower = earlier)

**Referential Integrity**: The combination of ``(segment_category, segment_vector, segment_value)``
must reference a valid segment that exists in ``segments.json``.

**Example**:

.. code-block:: json

   [
     {
       "persona_name": "Urban Tech-Savvy Millennial",
       "segment_category": "DEMOGRAPHIC",
       "segment_vector": "Age",
       "segment_value": "25-34 (Millennials - Younger)",
       "order_index": 0
     },
     {
       "persona_name": "Urban Tech-Savvy Millennial",
       "segment_category": "BEHAVIORAL",
       "segment_vector": "Innovation Adoption",
       "segment_value": "Early Adopters (13.5%)",
       "order_index": 1
     },
     {
       "persona_name": "Urban Tech-Savvy Millennial",
       "segment_category": "PSYCHOGRAPHIC",
       "segment_vector": "Core Values",
       "segment_value": "Innovation & Progress",
       "order_index": 2
     }
   ]

Import Commands
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Import segments
   uv run manage.py import_segments
   uv run manage.py import_segments --dry-run  # Preview without importing

   # Export segments
   uv run manage.py export_segments
   uv run manage.py export_segments --dir custom/

   # Import personas (requires segments to exist)
   uv run manage.py import_personas
   uv run manage.py import_personas --dry-run

   # Export personas
   uv run manage.py export_personas
   uv run manage.py export_personas --dir custom/

See :doc:`/user/segmentation` for comprehensive documentation on the segmentation framework,
including theoretical foundations (VALS, Rogers' Innovation Adoption Curve, AIO variables) and
best practices for building audience personas.
