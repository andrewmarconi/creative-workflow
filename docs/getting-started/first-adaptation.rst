Your First Adaptation
=====================

This tutorial walks you through creating a culturally adapted TV spot using the multi-agent pipeline. By the end, you'll have an origin script adapted for a new market, with a generated storyboard.

.. note::

   Make sure you've completed :doc:`installation` and have all services running via ``./start.sh``. Familiarity with :doc:`first-image` is helpful but not required.

Overview
--------

The adaptation workflow has five steps:

1. **Create a Brand** — define voice, values, and guidelines
2. **Create a Campaign** — the container for your TV spot project
3. **Create the origin** — a VideoAdUnit with the original script
4. **Create an adaptation** — target a new market; the pipeline runs automatically
5. **Generate a storyboard** — turn the adapted script into images

Step 1: Create a Brand
-----------------------

Navigate to **TV Spots > Brands > Add Brand**.

Fill in:

**Code** (required)
   A short unique identifier, e.g. ``ACME``.

**Name** (required)
   Display name, e.g. ``ACME Corp``.

**Guidelines** (recommended)
   Brand voice, values, visual identity, and messaging rules. This is what the brand evaluation gate checks against during adaptation. For example::

      Voice: Warm, approachable, optimistic. Avoid sarcasm.
      Values: Family, togetherness, authentic moments.
      Visual Identity: Bright colors, natural lighting, real people (not models).
      Messaging: Always lead with emotional benefit, product secondary.

**Insights** (optional)
   Structured brand insights as a JSON array::

      [
        {"heading": "Core Positioning", "points": ["Family snacking moments", "Authentic, unscripted feel"]},
        {"heading": "Visual Guidelines", "points": ["Warm color palette", "Natural lighting only"]}
      ]

Click **Save**.

Step 2: Create a Campaign
--------------------------

Navigate to **TV Spots > Campaigns > Add Campaign**.

Fill in:

**Job ID** (required)
   A unique tracking identifier, e.g. ``ACME-2024-SUMMER``.

**Client Name** (required)
   e.g. ``ACME Corp``.

**Script Title** (required)
   e.g. ``Summer Moments 2024``.

**Brand** (recommended)
   Select the brand you just created. This applies as the default for all ad units in the campaign.

**Product Name** (optional)
   e.g. ``ACME Chips Classic``.

Click **Save**.

Step 3: Create the Origin VideoAdUnit
--------------------------------------

The origin represents your original TV spot script — the source material that will be adapted.

Navigate to your Campaign's detail page and click **Create Origin Ad Unit**, or go to **TV Spots > Video Ad Units > Add Video Ad Unit** directly.

Fill in:

**Campaign** (required)
   Select the campaign you just created.

**Code** (required)
   e.g. ``ORIGIN``.

**Title** (required)
   e.g. ``US English Origin``.

**Origin or Adaptation**
   Set to **Origin**.

**Language** (required)
   The language of the original script, e.g. ``en-US``.

**Duration** (optional)
   Spot length in seconds, e.g. ``30``.

Click **Save**, then add script rows.

Adding Script Rows
^^^^^^^^^^^^^^^^^^

On the VideoAdUnit detail page, add rows using the **Script Rows** inline:

.. list-table::
   :header-rows: 1
   :widths: 10 15 40 35

   * - Shot
     - Timecode
     - Visual
     - Audio
   * - 01
     - 00:00:00
     - Wide shot of a sun-drenched backyard. A family sets up a picnic table.
     - Music: Upbeat acoustic guitar
   * - 02
     - 00:05:00
     - Close-up of hands opening a bag of ACME Chips. Golden chips catch the sunlight.
     - VO: "Some moments just call for the perfect crunch."
   * - 03
     - 00:12:00
     - Kids and parents laughing, passing the bag around the table.
     - VO: "ACME Chips. Made for moments like these."
   * - 04
     - 00:22:00
     - Product hero shot: bag of ACME Chips against a sunset backdrop.
     - VO: "ACME Chips. Crunch into summer."
   * - 05
     - 00:27:00
     - End card: ACME logo with tagline.
     - SFX: Chip crunch sound

Save after adding all rows.

Step 4: Create an Adaptation
-----------------------------

This is where the multi-agent pipeline takes over. Navigate to your Campaign and click **Create Adaptation**, or create a new VideoAdUnit directly.

Fill in:

**Campaign** (required)
   Same campaign as the origin.

**Source Ad Unit** (required)
   Select the origin VideoAdUnit you just created.

**Origin or Adaptation**
   Set to **Adaptation**.

**Region** (required)
   The target market region, e.g. ``DACH`` (Germany/Austria/Switzerland).

**Country** (optional)
   Specific country within the region, e.g. ``Germany``.

**Language** (required)
   Target language, e.g. ``de-DE``.

**Brand** (optional)
   Override the campaign brand if the adaptation uses a different brand name in this market.

**Persona** (optional)
   Target audience persona, e.g. ``Budget-Conscious First-Timer``.

Click **Save**.

The Pipeline Runs Automatically
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On save, the adaptation task is **automatically queued** to Celery. The multi-agent pipeline executes 7 nodes:

1. **Concept Analyst** — extracts core themes, emotions, and narrative structure from the origin script
2. **Cultural Researcher** — investigates the target market's values, communication styles, and cultural sensitivities
3. **Writer** — adapts the script with culturally appropriate visuals and dialogue
4. **Format Evaluator** — verifies visual descriptions are in English, with only voiceover and supers in the target language (including English translations)
5. **Cultural Evaluator** — validates cultural sensitivity and appropriateness
6. **Concept Evaluator** — ensures the adapted script preserves the original campaign intent
7. **Brand Evaluator** — checks brand voice, values, visual identity, and messaging consistency

If any evaluation gate fails, the writer automatically revises the script (up to 3 retries per gate).

Monitor progress on the VideoAdUnit detail page — the status updates through each pipeline stage.

Viewing the Results
^^^^^^^^^^^^^^^^^^^

Once the pipeline completes (status: **completed**), the VideoAdUnit detail page shows:

**Concept Brief**
   JSON output from the concept analyst: core themes, emotional arc, narrative structure extracted from the origin.

**Cultural Brief**
   JSON output from the cultural researcher: target market insights, values, communication patterns, potential sensitivities.

**Evaluation History**
   Array of results from each evaluation gate: pass/fail decisions with reasoning.

**Adapted Script Rows**
   The adapted script, saved as AdUnitScriptRow records. Visual descriptions remain in English; voiceover and supers are in the target language with English translations in brackets.

Step 5: Generate a Storyboard
------------------------------

With the adapted script complete, you can generate visual storyboard frames.

Navigate to the completed adaptation VideoAdUnit and click **Generate Storyboard**, or go to **TV Spots > Storyboards > Add Storyboard**.

Fill in:

**Video Ad Unit** (required)
   Select the completed adaptation.

**Diffusion Model** (required)
   Choose the image generation model. Good choices:

   - **Flux.1-dev** — high quality, good for presentation storyboards
   - **SDXL Turbo** — fast iterations for draft storyboards

**LoRA Model** (optional)
   Apply a visual style to all generated frames.

**Images Per Row** (optional)
   Number of image variations per script row. Default: 1.

Click **Save**. The storyboard task is automatically queued.

The system:

1. Generates image prompts from each script row's visual description
2. Creates a DiffusionJob for each prompt
3. Queues all jobs to the Celery worker
4. Images generate sequentially (one at a time to manage GPU memory)

Monitor progress on the Storyboard detail page — it shows total jobs, completed jobs, and a progress percentage.

Once complete, the storyboard displays frame-by-frame with the generated images alongside the script rows.

What Just Happened
------------------

In this tutorial you:

- Defined brand guidelines that the pipeline evaluates against
- Created a campaign with an origin TV spot script
- Ran a 7-node multi-agent pipeline that produced a concept brief, cultural brief, and culturally adapted script
- Generated a visual storyboard from the adapted script using diffusion models

The entire adaptation — from origin script to adapted storyboard — was driven by the Django admin UI with Celery handling all background processing.

Next Steps
----------

- :doc:`/guides/pipeline/prompt-templates` — edit the LLM prompts that drive each pipeline node
- :doc:`/guides/audiences-brands/segments-personas` — create detailed audience personas for more targeted adaptations
- :doc:`/guides/image-generation/loras` — apply LoRA styles to your storyboard frames
