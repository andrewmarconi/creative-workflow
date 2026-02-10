Data Schemas (JSON)
===================

Field-by-field specification for all JSON data files under ``data/``.

presets.json
------------

Top-level structure with two arrays:

.. code-block:: text

   { "models": [...], "loras": [...] }

See :doc:`configuration` for the full model and LoRA field reference.

llm_models.json
---------------

LLM model configurations for text generation.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``model_id``
     - string
     - Yes
     - HuggingFace identifier (e.g., ``Qwen/Qwen2.5-7B-Instruct``)
   * - ``name``
     - string
     - Yes
     - Display name (e.g., "Qwen 2.5 7B")
   * - ``notes``
     - string
     - No
     - Capabilities or use-case notes
   * - ``is_active``
     - bool
     - Yes
     - Whether model is available for selection
   * - ``load_in_4bit``
     - bool
     - Yes
     - Whether to use 4-bit quantization

Example:

.. code-block:: json

   {
     "model_id": "Qwen/Qwen2.5-7B-Instruct",
     "name": "Qwen 2.5 7B",
     "notes": "Strong multilingual, best for CJK languages",
     "is_active": true,
     "load_in_4bit": true
   }

regions.json
------------

Geographic regions for adaptation targeting.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``code``
     - string
     - Yes
     - Region code (e.g., ``NA``, ``LATAM``, ``DACH``)
   * - ``name``
     - string
     - Yes
     - Full name (e.g., "North America")
   * - ``description``
     - string
     - No
     - Regional description
   * - ``insights``
     - array
     - Yes
     - ``[{heading, points[]}]`` --- cultural patterns and media environment
   * - ``is_active``
     - bool
     - Yes
     - Whether region is available

countries.json
--------------

Countries with default language references.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``code``
     - string
     - Yes
     - ISO 3166-1 alpha-2 code (e.g., ``US``, ``GB``, ``DE``)
   * - ``name``
     - string
     - Yes
     - Full country name
   * - ``default_language``
     - string
     - Yes
     - FK to ``languages.json[].code`` (e.g., ``en-US``)
   * - ``insights``
     - array
     - Yes
     - ``[{heading, points[]}]`` --- regulatory and cultural considerations
   * - ``notes``
     - string
     - No
     - Additional notes
   * - ``is_active``
     - bool
     - Yes
     - Whether country is available

languages.json
--------------

Languages with LLM model references.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``code``
     - string
     - Yes
     - IETF BCP 47 code (e.g., ``en-US``, ``de-AT``, ``zh-CN``)
   * - ``name``
     - string
     - Yes
     - Full name with region (e.g., "English (United States)")
   * - ``base_language``
     - string
     - Yes
     - 2-letter base code (e.g., ``en``, ``de``)
   * - ``primary_model``
     - string
     - Yes
     - FK to ``llm_models.json[].model_id``
   * - ``alternative_models``
     - array
     - Yes
     - Array of alternative ``model_id`` strings (can be empty)
   * - ``insights``
     - array
     - Yes
     - ``[{heading, points[]}]`` --- language characteristics and localization guidance
   * - ``notes``
     - string
     - No
     - Additional notes
   * - ``is_active``
     - bool
     - Yes
     - Whether language is available

country_regions.json
--------------------

Many-to-many mapping between countries and regions.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``country_code``
     - string
     - Yes
     - FK to ``countries.json[].code``
   * - ``region_code``
     - string
     - Yes
     - FK to ``regions.json[].code``

A country can belong to multiple regions (e.g., Australia maps to both ``ANZ`` and ``APAC``).

country_languages.json
----------------------

Many-to-many mapping between countries and languages.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``country_code``
     - string
     - Yes
     - FK to ``countries.json[].code``
   * - ``language_code``
     - string
     - Yes
     - FK to ``languages.json[].code``
   * - ``is_primary``
     - bool
     - Yes
     - Whether this is the country's primary language

Multilingual countries have multiple entries with typically one marked ``is_primary: true``.

prompt_templates.json
---------------------

Jinja2 prompt templates for LLM interactions.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``slug``
     - string
     - Yes
     - Unique identifier (e.g., ``adaptation``, ``eval-brand``)
   * - ``name``
     - string
     - Yes
     - Display name
   * - ``category``
     - string
     - Yes
     - One of: ``adaptation``, ``enhancement``, ``concept``, ``evaluation``
   * - ``description``
     - string
     - Yes
     - What the template does
   * - ``template``
     - string
     - Yes
     - Jinja2 template body with ``{{ variables }}``
   * - ``expected_variables``
     - object
     - Yes
     - Variable schema (currently ``{}``)
   * - ``version``
     - int
     - Yes
     - Auto-incrementing version number

See :doc:`/guides/pipeline/prompt-templates` for template editing and versioning.

segments.json
-------------

Audience segments across three categories.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``category``
     - string
     - Yes
     - ``DEMOGRAPHIC``, ``BEHAVIORAL``, or ``PSYCHOGRAPHIC``
   * - ``vector``
     - string
     - Yes
     - Segmentation dimension (e.g., "Household Income", "Usage Pattern")
   * - ``value``
     - string
     - Yes
     - Position on the dimension (e.g., "Middle-Income", "First-Time Users")
   * - ``description``
     - string
     - No
     - Segment description
   * - ``insights``
     - array
     - No
     - ``[{heading, points[]}]`` --- advertising approach guidance
   * - ``is_active``
     - bool
     - Yes
     - Whether segment is available

The composite ``(category, vector, value)`` must be unique.

personas.json
-------------

Audience personas combining geographic and segment targeting.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``name``
     - string
     - Yes
     - Persona name (e.g., "Budget-Conscious First-Timer")
   * - ``description``
     - string
     - No
     - Persona description
   * - ``region_code``
     - string
     - No
     - FK to ``regions.json[].code``
   * - ``country_code``
     - string
     - No
     - FK to ``countries.json[].code``
   * - ``language_code``
     - string
     - No
     - FK to ``languages.json[].code``
   * - ``is_active``
     - bool
     - Yes
     - Whether persona is available

persona_segments.json
---------------------

Many-to-many mapping between personas and segments.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``persona_name``
     - string
     - Yes
     - FK to ``personas.json[].name``
   * - ``segment_category``
     - string
     - Yes
     - Segment category (e.g., ``DEMOGRAPHIC``)
   * - ``segment_vector``
     - string
     - Yes
     - Segment vector (e.g., "Household Income")
   * - ``segment_value``
     - string
     - Yes
     - Segment value (e.g., "Middle-Income")
   * - ``order_index``
     - int
     - No
     - Display ordering within the persona

brands.json
-----------

Brand reference data for the brand evaluation gate.

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``code``
     - string
     - Yes
     - Unique identifier (e.g., ``LAYS``, ``WALKERS``)
   * - ``name``
     - string
     - Yes
     - Display name
   * - ``description``
     - string
     - No
     - Brand overview and positioning
   * - ``guidelines``
     - string
     - No
     - Free-text brand voice, values, visual identity rules
   * - ``insights``
     - array
     - No
     - ``[{heading, points[]}]`` --- structured brand patterns
   * - ``is_active``
     - bool
     - Yes
     - Whether brand is available

See :doc:`/guides/audiences-brands/brand-configuration` for usage in the evaluation gate.

example_tvspot.json
-------------------

TV spot import format used by ``import_tvspot``.

**Top-Level Fields**

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``client_name``
     - string
     - Yes
     - Client or advertiser name
   * - ``brand_name``
     - string
     - Yes
     - Brand name
   * - ``script_title``
     - string
     - Yes
     - Campaign or script title
   * - ``total_runtime_seconds``
     - number
     - Yes
     - Total spot duration in seconds
   * - ``job_id``
     - string
     - Yes
     - Unique job identifier (e.g., ``ACME-2024-001``)
   * - ``language``
     - string
     - Yes
     - Language code (e.g., ``en-US``)
   * - ``notes``
     - string
     - No
     - Production notes
   * - ``script_rows``
     - array
     - Yes
     - Array of script row objects

**Script Row Fields**

.. list-table::
   :header-rows: 1
   :widths: 25 10 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``shot_number``
     - string
     - Yes
     - Shot identifier (e.g., ``01``, ``02``)
   * - ``timecode_start``
     - string
     - Yes
     - Timecode in ``HH:MM:SS:FF`` format
   * - ``duration_seconds``
     - number
     - Yes
     - Shot duration in seconds
   * - ``visual_text``
     - string
     - Yes
     - Scene description (framing, setting, talent, on-screen text)
   * - ``audio_text``
     - string
     - Yes
     - Audio specification (SFX, MUSIC, VO, DIALOGUE)

See :doc:`/guides/tv-spot-adaptation/importing-tvspots` for import instructions and validation rules.

Insights Schema
---------------

Multiple models share a common insights structure:

.. code-block:: json

   [
     {
       "heading": "Section Title",
       "points": [
         "First point",
         "Second point"
       ]
     }
   ]

Used by: Region, Country, Language, Segment, and Brand models. The ``compose_insights()`` function in ``src/cw/lib/insights.py`` aggregates insights from multiple sources in hierarchical order.

Relationship Diagram
--------------------

.. mermaid::

   erDiagram
       LLM_MODELS ||--o{ LANGUAGES : "primary_model"
       REGIONS ||--o{ COUNTRY_REGIONS : ""
       COUNTRIES ||--o{ COUNTRY_REGIONS : ""
       COUNTRIES ||--o{ COUNTRY_LANGUAGES : ""
       LANGUAGES ||--o{ COUNTRY_LANGUAGES : ""
       COUNTRIES }o--|| LANGUAGES : "default_language"
       PERSONAS }o--o| REGIONS : "region_code"
       PERSONAS }o--o| COUNTRIES : "country_code"
       PERSONAS }o--o| LANGUAGES : "language_code"
       PERSONAS ||--o{ PERSONA_SEGMENTS : ""
       SEGMENTS ||--o{ PERSONA_SEGMENTS : ""
