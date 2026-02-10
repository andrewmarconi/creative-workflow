Audience Targeting
==================

This page explains how geographic and non-geographic audience data is structured, composed into hierarchical insights, and fed into the adaptation pipeline.

Data Model
----------

Audience targeting combines two dimensions: **geographic** (where the audience is) and **non-geographic** (who the audience is). These are modeled separately and brought together through Personas.

.. mermaid::

   erDiagram
       Region ||--o{ CountryRegion : contains
       Country ||--o{ CountryRegion : belongs_to
       Country ||--o{ CountryLanguage : speaks
       Language ||--o{ CountryLanguage : spoken_in
       Language }o--|| LLMModel : primary_model
       Language }o--o{ LLMModel : alternative_models

       Persona }o--o| Region : targets
       Persona }o--o| Country : targets
       Persona }o--o| Language : targets
       Persona ||--o{ PersonaSegment : includes
       Segment ||--o{ PersonaSegment : included_in

Geographic Hierarchy
--------------------

The geographic hierarchy has three levels, each progressively more specific:

**Region**
   Cultural or market groupings — not strictly political boundaries. A region like ``DACH`` (Germany, Austria, Switzerland) groups countries that share cultural characteristics relevant to advertising adaptation.

   Fields: ``code``, ``name``, ``description``, ``insights`` (JSON), ``is_active``

**Country**
   Political and regulatory entities. Countries can belong to **multiple regions** (e.g., Switzerland belongs to both DACH and EU-WEST) via the ``CountryRegion`` many-to-many table.

   Each country has a ``default_language`` and can have multiple languages via the ``CountryLanguage`` table, with an ``is_primary`` flag indicating the official or dominant language.

   Fields: ``code`` (ISO 3166-1 alpha-2), ``name``, ``default_language`` (FK), ``insights`` (JSON), ``notes``, ``is_active``

**Language**
   Locale-specific language variants (e.g., ``en-US``, ``fr-CA``, ``de-CH``). Each language references a ``primary_model`` — the LLM best suited for generating content in that language — and optionally ``alternative_models`` for fallback.

   Fields: ``code`` (ISO 639 + country), ``name``, ``base_language``, ``primary_model`` (FK to LLMModel), ``insights`` (JSON), ``notes``, ``is_active``

The many-to-many relationships are modeled with explicit through tables (``CountryRegion``, ``CountryLanguage``, ``LanguageAlternativeModel``) to support additional metadata like ``is_primary``.

Non-Geographic Segments
-----------------------

Segments capture audience characteristics that are independent of geography. Each segment has a **category**, **vector** (the dimension being measured), and **value** (the position on that dimension).

Three segment categories:

**Demographic**
   Observable characteristics of the audience.

   Examples: Household Income → Middle-Income, Age Group → 25–34, Education → University-Educated

**Behavioral**
   Actions and usage patterns.

   Examples: Usage Pattern → First-Time Users, Purchase Frequency → Occasional Buyers, Media Consumption → Mobile-First

**Psychographic**
   Attitudes, values, and motivations.

   Examples: Emotional Driver → Nostalgia, Lifestyle → Health-Conscious, Values → Tradition-Oriented

Each segment carries its own ``insights`` JSON field with guidance relevant to that audience characteristic — for example, messaging strategies for budget-conscious consumers or visual preferences for nostalgia-driven audiences.

Personas
--------

A Persona is a **named composite audience profile** that combines geographic and non-geographic targeting into a single entity:

- **Geographic targeting** — optional Region, Country, and Language FKs
- **Non-geographic segments** — many-to-many relationship to Segments via ``PersonaSegment``
- **Metadata** — name, description, active flag

For example, a persona named "Budget-Conscious First-Timer" might combine:

- Geographic: North America / United States / en-US
- Demographic: Household Income → Middle-Income
- Behavioral: Usage Pattern → First-Time Users
- Psychographic: Emotional Driver → Value-Seeking

When a Persona is assigned to an adaptation VideoAdUnit, its geographic and segment data are included in the insights composition that the pipeline receives.

Insights
--------

Every level of the audience hierarchy carries structured insights as a JSON array:

.. code-block:: json

   [
     {
       "heading": "Communication Style",
       "points": [
         "Direct and informal tone preferred",
         "Humor is effective but avoid sarcasm",
         "Family-oriented messaging resonates strongly"
       ]
     },
     {
       "heading": "Visual Preferences",
       "points": [
         "Bright, warm color palettes",
         "Real people over stylized imagery",
         "Outdoor and community settings"
       ]
     }
   ]

Insights are stored on Regions, Countries, Languages, and Segments. Each model provides an ``insights_as_markdown()`` method that renders the JSON into readable Markdown with headings and bullet points.

Insights Composition
--------------------

When the adaptation pipeline runs, it aggregates insights hierarchically from all relevant audience sources into a single Markdown document that becomes part of the pipeline context.

The composition order (from ``compose_insights_as_markdown()``):

1. **Region insights** — broad cultural context (if a region is set)
2. **Country insights** — country-specific guidance (if a country is set)
3. **Language insights** — language and locale-specific guidance (always present)
4. **Persona segment insights** — each segment's insights, ordered by category and vector (if a persona is set)

The result is a Markdown document with an H1 header identifying the target (e.g., "Adaptation Guidance for Budget-Conscious First-Timer — DACH / Germany / (de-DE)") and H2 sections for each insight source.

This composed document is passed to the pipeline as ``target_market_rules`` and used by the Cultural Researcher and evaluation gates as context for their analysis.

How It Feeds the Pipeline
-------------------------

The audience data enters the pipeline at initialization (``build_initial_state()``):

- **Target market name** — constructed from persona name or region/country/language
- **Target market language** — the language name (e.g., "German")
- **Language code** — the locale code (e.g., "de-DE")
- **Target market rules** — the composed insights Markdown document
- **Brand guidelines** — from the VideoAdUnit's effective brand

The Cultural Researcher uses the target market rules to produce culturally informed substitutions and recommendations. The evaluation gates reference them when validating cultural appropriateness and format compliance.

The Language model's ``primary_model`` FK also determines which LLM the writer node defaults to, ensuring the script is generated by a model suited to the target language.
