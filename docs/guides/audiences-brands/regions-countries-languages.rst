Regions, Countries & Languages
==============================

This guide covers managing the geographic reference data that drives market targeting and pipeline model selection.

Data Model
----------

Three models form a geographic hierarchy for adaptation targeting:

.. mermaid::

   erDiagram
       Region ||--o{ CountryRegion : "contains"
       Country ||--o{ CountryRegion : "belongs to"
       Country ||--o{ CountryLanguage : "speaks"
       Language ||--o{ CountryLanguage : "spoken in"
       Language }o--|| LLMModel : "primary model"
       Language ||--o{ LanguageAlternativeModel : "alternatives"
       Country }o--o| Language : "default language"

Region
^^^^^^

Cultural or market groupings that span multiple countries:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``code``
     - Short identifier (e.g., ``NA``, ``NORDICS``, ``DACH``, ``LATAM``, ``EU-WEST``)
   * - ``name``
     - Display name (e.g., "North America", "DACH")
   * - ``insights``
     - Regional cultural patterns as ``[{heading, points[]}]`` JSON
   * - ``is_active``
     - Whether the region is available for targeting

Regional insights capture broad cultural patterns shared across countries — e.g., Nordic minimalism, North American directness.

Country
^^^^^^^

Political and regulatory entities:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``code``
     - ISO 3166-1 alpha-2 code (e.g., ``US``, ``DE``, ``JP``)
   * - ``name``
     - Official country name
   * - ``default_language``
     - FK to Language — the primary/default language for this country
   * - ``insights``
     - Country-specific regulatory and cultural rules
   * - ``regions``
     - M2M to Region via ``CountryRegion`` — a country can belong to multiple regions
   * - ``languages``
     - M2M to Language via ``CountryLanguage`` — all languages spoken in this country

Language
^^^^^^^^

Language variants with locale codes:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``code``
     - ISO 639 + country locale (e.g., ``en-US``, ``fr-CA``, ``de-CH``)
   * - ``base_language``
     - ISO 639-1 base code (e.g., ``en``, ``fr``, ``de``) — groups related locales
   * - ``primary_model``
     - FK to LLMModel — recommended model for generating content in this language
   * - ``alternative_models``
     - M2M to LLMModel via ``LanguageAlternativeModel`` — fallback models
   * - ``insights``
     - Language-specific localization guidance

Many-to-Many Relationships
^^^^^^^^^^^^^^^^^^^^^^^^^^

- **CountryRegion** — links countries to regions (e.g., Switzerland in both DACH and EU-WEST)
- **CountryLanguage** — links countries to languages, with ``is_primary`` flag marking the official language
- **LanguageAlternativeModel** — links languages to fallback LLM models

Adding a New Market
-------------------

To add a new target market (e.g., South Korea):

1. **Create the Language** (if it doesn't exist):

   - Navigate to **Audiences > Languages > Add Language**
   - Set code to ``ko-KR``, name to "Korean (South Korea)", base language to ``ko``
   - Select a primary LLM model (e.g., Qwen2.5-7B-Instruct)
   - Add localization insights

2. **Create the Country**:

   - Navigate to **Audiences > Countries > Add Country**
   - Set code to ``KR``, name to "South Korea"
   - Set default language to ``ko-KR``
   - Add regulatory and cultural insights

3. **Link to Regions** (via CountryRegion):

   - Add ``KR`` to the ``APAC`` region (or create the region first if it doesn't exist)

4. **Link Languages** (via CountryLanguage):

   - Add ``ko-KR`` as primary language for South Korea

5. **Sync** — if using JSON files, export updated data:

   .. code-block:: bash

      uv run manage.py export_reference_data

Language-to-LLM Model Linking
-----------------------------

Each language has a **primary model** — the recommended LLM for generating content in that language. This drives the adaptation pipeline's model resolution chain:

1. Ad Unit ``pipeline_model_config`` override
2. PipelineSettings node default
3. PipelineSettings global default
4. **Language primary model** (fallback)

The **writer** node specifically defaults to the language's primary model (instead of the global default), since it produces the target-language content.

Alternative models are available as fallbacks and can be selected via the ad unit or pipeline settings overrides.

Insights Structure
------------------

All three models (Region, Country, Language) share the same insights JSON schema:

.. code-block:: json

   [
     {
       "heading": "Communication Style",
       "points": [
         "Prefer indirect, high-context communication",
         "Formality expected in business settings"
       ]
     },
     {
       "heading": "Visual Preferences",
       "points": [
         "Clean, minimalist layouts preferred",
         "Subtle color palettes resonate better than bold primaries"
       ]
     }
   ]

These insights are composed hierarchically by ``compose_insights()`` (see :doc:`/concepts/audience-targeting`) and passed to the adaptation pipeline as context for the cultural research and writing nodes.

Import & Export
---------------

Geographic reference data is stored in separate JSON files under ``data/``:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - File
     - Contents
   * - ``data/llm_models.json``
     - LLM models for text generation
   * - ``data/regions.json``
     - Geographic regions
   * - ``data/countries.json``
     - Countries with default language references
   * - ``data/languages.json``
     - Languages with primary model references
   * - ``data/country_regions.json``
     - Country-to-Region M2M mappings
   * - ``data/country_languages.json``
     - Country-to-Language M2M mappings (with ``is_primary``)

Commands:

.. code-block:: bash

   # Export all reference data to data/
   uv run manage.py export_reference_data

   # Export to a custom directory
   uv run manage.py export_reference_data --dir custom/

   # Import from data/ (dependency-ordered)
   uv run manage.py import_reference_data

   # Preview without importing
   uv run manage.py import_reference_data --dry-run

Import processes files in dependency order: LLM Models → Regions → Countries → Languages → M2M mappings.
