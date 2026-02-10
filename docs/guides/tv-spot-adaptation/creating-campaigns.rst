Creating a Campaign
===================

This guide covers setting up a new TV spot campaign — the top-level container for all ad units, scripts, and storyboards.

What Is a Campaign?
-------------------

A **Campaign** is the top-level container in the TV spot hierarchy. It represents a single advertising project and holds:

- Client and product metadata
- The original script data (JSON)
- A link to a **Brand** for brand evaluation during adaptation
- All **Ad Units** (origin and adaptations) created under it

.. mermaid::

   erDiagram
       Brand ||--o{ Campaign : "primary brand"
       Campaign ||--|{ VideoAdUnit : "contains"
       VideoAdUnit ||--|{ AdUnitScriptRow : "has"
       VideoAdUnit ||--o{ Storyboard : "visualized by"

Creating a Campaign in the Admin
---------------------------------

1. Navigate to **TV Spots > Campaigns > Add Campaign**
2. Fill in the required fields:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Description
   * - **Job ID**
     - Unique tracking identifier (e.g., ``ACME-2024-001``). Must be unique across all campaigns.
   * - **Script Title**
     - Campaign or script name (e.g., "Morning Boost 30s")
   * - **Client Name**
     - Client organization name
   * - **Product Name**
     - Product being advertised (optional)
   * - **Brand**
     - Link to a Brand record for brand evaluation during adaptation (optional but recommended)
   * - **Original Script Data**
     - The origin script as JSON (optional — can also be created via ``import_tvspot`` or video analysis)

3. Save the campaign

Linking a Brand
---------------

Linking a Brand to a campaign enables the **brand evaluation gate** in the adaptation pipeline. The evaluator checks adapted scripts against the brand's:

- **Voice** — tone, personality, communication style
- **Values** — core principles, messaging themes
- **Guidelines** — visual identity, naming rules, tagline usage
- **Insights** — market-specific patterns and preferences

To link a brand:

1. Create the Brand record first (under **TV Spots > Brands**)
2. Select it in the Campaign's **Brand** dropdown

Adaptations can also override the campaign's brand with a market-specific variant (e.g., Lay's → Walkers for the UK market). See :doc:`ad-units` for details.

Setting Original Script Data
-----------------------------

The ``original_script_data`` field stores the campaign's source script as JSON. This data is used by the adaptation pipeline's concept extraction node to analyze the origin script's themes, structure, and intent.

The JSON format matches the import format:

.. code-block:: json

   {
     "script_rows": [
       {
         "shot_number": "01",
         "timecode_start": "00:00:00:00",
         "duration_seconds": 3.0,
         "visual_text": "Wide shot: Urban apartment...",
         "audio_text": "SFX: Alarm buzzing\nMUSIC: Soft instrumental"
       }
     ]
   }

For campaigns created via the ``import_tvspot`` command, this field is populated automatically. See :doc:`importing-tvspots` for the full JSON specification.

Campaign Lifecycle
------------------

A typical campaign flows through these stages:

1. **Create Campaign** — set up metadata and link a brand
2. **Create Origin Ad Unit** — add the source script (manually, via JSON import, or via video analysis)
3. **Create Adaptation Ad Units** — target specific markets with the adaptation pipeline
4. **Generate Storyboards** — visualize adapted scripts with diffusion models

Multiple adaptations can run in parallel under one campaign, each targeting a different region, country, or language.

Viewing Campaign Status
-----------------------

The campaign list view shows all campaigns sorted by creation date. Click a campaign to see:

- Campaign metadata (job ID, client, product, brand)
- All ad units created under it (origin and adaptations)
- Storyboards generated for each ad unit

Ad unit statuses update in real time as pipeline tasks complete. See :doc:`/concepts/observability` for monitoring task execution.
