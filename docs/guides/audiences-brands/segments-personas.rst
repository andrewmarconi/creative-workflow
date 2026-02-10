Segments & Personas
===================

This guide covers defining audience segments and composing them into personas for adaptation targeting.

Segments
--------

A **Segment** represents a single audience characteristic across three categories:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Category
     - What It Captures
     - Example Vectors
   * - **Demographic**
     - Who the audience is
     - Household Income, Age Group, Education Level
   * - **Behavioral**
     - How the audience acts
     - Usage Pattern, Purchase Frequency, Brand Loyalty
   * - **Psychographic**
     - Why the audience acts
     - Emotional Driver, Lifestyle Values, Aspiration

Each segment has three identifying fields:

- **Category** — one of ``DEMOGRAPHIC``, ``BEHAVIORAL``, ``PSYCHOGRAPHIC``
- **Vector** — the dimension being segmented (e.g., "Household Income")
- **Value** — the position on that dimension (e.g., "Middle-Income")

The combination of ``(category, vector, value)`` must be unique.

Creating a Segment
^^^^^^^^^^^^^^^^^^

1. Navigate to **Audiences > Segments > Add Segment**
2. Select the **Category**
3. Enter the **Vector** (dimension) and **Value** (position)
4. Optionally add a **Description** and **Insights**
5. Save

Segment Insights
^^^^^^^^^^^^^^^^

Like geographic models, segments support structured insights:

.. code-block:: json

   [
     {
       "heading": "Advertising Approach",
       "points": [
         "Value-focused messaging resonates strongly",
         "Emphasize cost-effectiveness and practical benefits",
         "Avoid luxury or aspirational positioning"
       ]
     }
   ]

These insights are included in the adaptation pipeline context when the segment is part of an active persona.

Personas
--------

A **Persona** combines geographic targeting (Region, Country, Language) with non-geographic segments to create a complete audience profile:

.. code-block:: text

   Persona: "Budget-Conscious First-Timer"
   ├── Geographic: North America / United States / en-US
   ├── Demographic: Household Income → Middle-Income
   ├── Behavioral: Usage Pattern → First-Time Users
   └── Psychographic: Emotional Driver → Nostalgia

Creating a Persona
^^^^^^^^^^^^^^^^^^

1. Navigate to **Audiences > Personas > Add Persona**
2. Enter a **Name** (e.g., "Budget-Conscious First-Timer")
3. Set geographic targeting:

   - **Region** — e.g., North America
   - **Country** — e.g., United States
   - **Language** — e.g., English (United States)

4. Add **Segments** via the inline PersonaSegment section — select from existing Demographic, Behavioral, and Psychographic segments
5. Save

Cascading Admin Selectors
^^^^^^^^^^^^^^^^^^^^^^^^^

The admin uses AJAX-powered cascading dropdowns:

- Selecting a **Region** filters the Country dropdown to show only countries in that region
- Selecting a **Country** filters the Language dropdown to show only languages for that country

This prevents invalid combinations (e.g., selecting Japanese language for a German country).

Linking Personas to Ad Units
-----------------------------

When creating an adaptation ad unit, select a **Persona** in the targeting section. This:

1. Pre-fills the Region, Country, and Language from the persona
2. Passes the persona's segment insights to the adaptation pipeline
3. Provides audience context for the cultural research and writing nodes

See :doc:`/guides/tv-spot-adaptation/ad-units` for details on configuring adaptation ad units.

How Personas Feed the Pipeline
------------------------------

The ``compose_insights()`` function in ``src/cw/lib/insights.py`` aggregates insights in order:

1. **Region** insights — broad cultural patterns
2. **Country** insights — regulatory and local cultural rules
3. **Language** insights — localization guidance
4. **Persona segments** — non-geographic audience insights (Demographic, Behavioral, Psychographic)

This hierarchical composition provides comprehensive context to the pipeline's cultural research and writer nodes, enabling audience-appropriate adaptations.

Import & Export
---------------

Segments and personas have separate import/export commands:

.. code-block:: bash

   # Segments
   uv run manage.py export_segments                # → data/segments.json
   uv run manage.py export_segments --dir custom/
   uv run manage.py import_segments                # ← data/segments.json
   uv run manage.py import_segments --dry-run

   # Personas
   uv run manage.py export_personas                # → data/personas.json + persona_segments.json
   uv run manage.py export_personas --dir custom/
   uv run manage.py import_personas                # ← data/personas.json
   uv run manage.py import_personas --dry-run

Persona export produces two files:

- ``personas.json`` — persona records with geographic references (by code)
- ``persona_segments.json`` — persona-to-segment mappings (by category/vector/value)

Import resolves references by code/value rather than by primary key, making data portable across environments.
