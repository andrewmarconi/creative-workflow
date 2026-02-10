Brand Configuration
===================

This guide covers setting up brand data for the brand evaluation gate in the adaptation pipeline.

Brand Model
-----------

A **Brand** record captures the identity, voice, and guidelines that the brand evaluation node checks adapted scripts against.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``code``
     - Short identifier, unique (e.g., ``LAYS``, ``WALKERS``, ``PEPSI``)
   * - ``name``
     - Display name (e.g., "Lay's", "Walkers")
   * - ``description``
     - Brand overview and positioning statement
   * - ``guidelines``
     - Free-text brand voice, values, visual identity, and messaging guidelines
   * - ``insights``
     - Structured brand patterns as ``[{heading, points[]}]`` JSON
   * - ``is_active``
     - Whether the brand is available for selection

Creating a Brand
^^^^^^^^^^^^^^^^

1. Navigate to **TV Spots > Brands > Add Brand**
2. Enter a **Code** and **Name**
3. Write the **Description** — positioning and brand essence
4. Write **Guidelines** — detailed instructions for the brand evaluation gate:

   .. code-block:: text

      Voice: Playful, energetic, youthful. Never corporate or stiff.
      Values: Fun, togetherness, everyday moments of joy.
      Visual Identity: Bold primary colors (red, yellow). Product always
      visible. No dark or moody imagery.
      Messaging: Keep taglines simple and memorable. Always end with
      the brand tagline "Life's Good with Lay's."
      Naming: Use market-specific brand name (Walkers in UK, Lay's elsewhere).

5. Add **Insights** for structured brand patterns:

   .. code-block:: json

      [
        {
          "heading": "Brand Voice",
          "points": [
            "Playful and conversational tone",
            "Avoid formal or corporate language",
            "Use humor where culturally appropriate"
          ]
        },
        {
          "heading": "Visual Consistency",
          "points": [
            "Product must appear in at least 2 shots",
            "Brand colors (red, yellow) should dominate the palette",
            "Logo visible in opening and closing frames"
          ]
        }
      ]

6. Save

How Brand Evaluation Works
--------------------------

The **brand evaluation gate** is the final evaluation node in the adaptation pipeline. It checks the adapted script against the brand's guidelines and insights:

1. The pipeline resolves the **effective brand** for the ad unit (ad unit override → campaign default)
2. The ``eval-brand`` prompt template receives the brand's ``guidelines`` and ``insights`` fields
3. The LLM evaluates whether the adapted script:

   - Maintains the brand's voice and tone
   - Preserves visual identity requirements
   - Uses correct brand naming for the target market
   - Aligns with brand values and messaging guidelines

4. If the evaluation fails, the script is sent back to the writer node for revision (up to 3 retries)

See :doc:`/concepts/adaptation-pipeline` for the full evaluation gate architecture.

Linking Brands
--------------

Brands connect to the adaptation workflow at two levels:

Campaign Level
^^^^^^^^^^^^^^

Every Campaign has an optional **Brand** FK. This is the default brand for all ad units under the campaign:

1. Navigate to **TV Spots > Campaigns**
2. Select or create a campaign
3. Set the **Brand** field

Ad Unit Level (Override)
^^^^^^^^^^^^^^^^^^^^^^^^

Individual ad units can override the campaign's brand. This handles market-specific trade names:

.. code-block:: text

   Campaign brand: Lay's (LAYS)

   US adaptation: uses campaign brand (Lay's)
   UK adaptation: overrides with Walkers (WALKERS)
   India adaptation: overrides with Lay's India (LAYS_IN)

The ``effective_brand`` property resolves this: ad unit brand first, then campaign brand.

To set an override:

1. Navigate to the adaptation **Video Ad Unit**
2. Set the **Brand** field to the market-specific brand
3. Save — the pipeline will use the override brand for evaluation

Guidelines vs. Insights
-----------------------

Both ``guidelines`` and ``insights`` inform the brand evaluation gate, but serve different purposes:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Field
     - Format
     - Best For
   * - **guidelines**
     - Free-text
     - Detailed, nuanced instructions — voice descriptions, naming rules, visual identity requirements, tone guidance
   * - **insights**
     - Structured JSON ``[{heading, points[]}]``
     - Bullet-point patterns — checkable rules, quantifiable requirements, categorical distinctions

Both fields are passed to the ``eval-brand`` prompt template. Use ``guidelines`` for prose-style brand books and ``insights`` for structured evaluation criteria.

Import & Export
---------------

Brand data is managed via dedicated commands:

.. code-block:: bash

   # Export brands to data/brands.json
   uv run manage.py export_brands

   # Export to a custom directory
   uv run manage.py export_brands --dir custom/

   # Import brands from data/brands.json
   uv run manage.py import_brands

   # Preview without importing
   uv run manage.py import_brands --dry-run

The JSON format includes all brand fields, referenced by ``code``:

.. code-block:: json

   [
     {
       "code": "LAYS",
       "name": "Lay's",
       "description": "Global snack brand...",
       "guidelines": "Voice: Playful, energetic...",
       "insights": [
         {
           "heading": "Brand Voice",
           "points": ["Playful tone", "Avoid formality"]
         }
       ],
       "is_active": true
     }
   ]
