Importing TV Spots (JSON)
=========================

This guide covers the JSON format for TV spot scripts and the ``import_tvspot`` management command for bulk creation.

JSON Format
-----------

TV spot scripts use a flat JSON structure with top-level metadata and an array of script rows.

Required Fields
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``client_name``
     - string
     - Client organization name
   * - ``script_title``
     - string
     - Campaign or script title
   * - ``total_runtime_seconds``
     - integer
     - Total spot duration in seconds (must be positive)
   * - ``job_id``
     - string
     - Unique tracking ID (e.g., ``ACME-2024-001``). Must be unique across all campaigns.
   * - ``script_rows``
     - array
     - Array of script row objects (at least one required)

Optional Fields
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``brand_name``
     - string
     - Brand name (for display purposes)
   * - ``language``
     - string
     - Language code (e.g., ``en-US``). Defaults to ``en-US``. Must exist in the database.
   * - ``notes``
     - string
     - Free-text notes or production context

Script Row Fields
^^^^^^^^^^^^^^^^^

Each script row represents one shot or scene:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Field
     - Type
     - Description
   * - ``visual_text`` *
     - string
     - Visual description: shot composition, talent direction, settings, supers. **Required, non-empty.**
   * - ``audio_text`` *
     - string
     - Audio content: voiceover, music cues, SFX, dialogue. **Required, non-empty.**
   * - ``shot_number``
     - string
     - Shot identifier (e.g., ``01``, ``02``). Auto-generated from index if omitted.
   * - ``timecode_start``
     - string
     - Timecode in ``HH:MM:SS:FF`` format (optional)
   * - ``duration_seconds``
     - float
     - Shot duration in seconds (optional)

Example JSON
^^^^^^^^^^^^

.. code-block:: json

   {
     "client_name": "Acme Corporation",
     "brand_name": "Acme Energy Drink",
     "script_title": "Morning Boost 30s",
     "total_runtime_seconds": 30,
     "job_id": "ACME-2024-001",
     "language": "en-US",
     "notes": "Q1 2024 campaign launch spot",
     "script_rows": [
       {
         "shot_number": "01",
         "timecode_start": "00:00:00:00",
         "duration_seconds": 3.0,
         "visual_text": "Wide shot: Urban apartment, early morning. Sunlight streaming through windows. TALENT (30s, professional) wakes up groggy, reaches for alarm clock.",
         "audio_text": "SFX: Alarm buzzing\nMUSIC: Soft, building instrumental"
       },
       {
         "shot_number": "02",
         "timecode_start": "00:00:03:00",
         "duration_seconds": 4.0,
         "visual_text": "Medium shot: Kitchen counter. TALENT opens refrigerator, pulls out ACME ENERGY DRINK can. Product hero shot with condensation.",
         "audio_text": "SFX: Refrigerator opening, can crack\nMUSIC: Energy builds"
       },
       {
         "shot_number": "03",
         "timecode_start": "00:00:07:00",
         "duration_seconds": 3.0,
         "visual_text": "Close-up: TALENT drinks. Expression transforms from tired to energized.",
         "audio_text": "VO: \"Acme Energy. The boost you need.\"\nMUSIC: Peak energy"
       }
     ]
   }

A complete 8-row example is available at ``data/example_tvspot.json``.

The import_tvspot Command
-------------------------

Usage
^^^^^

.. code-block:: bash

   # Import a TV spot
   uv run manage.py import_tvspot path/to/spot.json

   # Validate without creating records
   uv run manage.py import_tvspot path/to/spot.json --dry-run

What the Command Does
^^^^^^^^^^^^^^^^^^^^^

1. **Validates the JSON** — checks required fields, types, and script row structure
2. **Checks for duplicates** — ensures the ``job_id`` doesn't already exist
3. **Creates records** in a single database transaction:

   - One **Campaign** (from top-level metadata)
   - One **origin VideoAdUnit** (code ``ORIGIN``, linked to the campaign)
   - One **AdUnitScriptRow** per script row (linked to the origin ad unit)

4. **Resolves the language** — looks up the ``language`` code in the database (requires reference data to be imported first)

Prerequisites
^^^^^^^^^^^^^

Before importing, ensure reference data is loaded:

.. code-block:: bash

   uv run manage.py import_reference_data

This populates the Language table that the import command references.

Validation Rules
^^^^^^^^^^^^^^^^

The command validates the following:

- All required top-level fields are present
- ``script_rows`` is a non-empty array
- ``total_runtime_seconds`` is a positive integer
- Each script row has non-empty ``visual_text`` and ``audio_text``
- ``job_id`` is unique (no existing campaign with the same ID)
- ``language`` code exists in the database

Dry Run Output
^^^^^^^^^^^^^^

.. code-block:: text

   Reading TV spot from: data/example_tvspot.json
   DRY RUN - validating only
     ✓ JSON validation passed

   TV Spot Details:
     Client: Acme Corporation
     Title: Morning Boost 30s
     TRT: 30s
     Job ID: ACME-2024-001
     Script rows: 8

   Validation complete (dry run)

Import Output
^^^^^^^^^^^^^

.. code-block:: text

   Reading TV spot from: data/example_tvspot.json
     ✓ JSON validation passed

   TV Spot Details:
     Client: Acme Corporation
     Title: Morning Boost 30s
     TRT: 30s
     Job ID: ACME-2024-001
     Script rows: 8

     ✓ Created TvSpot #1
     ✓ Created TvSpotVersion #1 (origin, language=en-US)
     ✓ Created 8 script rows

   ============================================================
   Import Complete!
     TV Spot ID: 1
     Version ID: 1
   ============================================================

Error Handling
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Error
     - Cause
   * - ``File not found``
     - The specified path doesn't exist
   * - ``Invalid JSON``
     - File contains malformed JSON
   * - ``Missing required field``
     - A required top-level field is absent
   * - ``script_rows[N] missing or empty visual_text``
     - A script row is missing its visual description
   * - ``TV Spot with job_id already exists``
     - A campaign with the same ``job_id`` is already in the database
   * - ``Language 'xx-XX' not found``
     - The specified language code hasn't been imported. Run ``import_reference_data`` first.

All imports are wrapped in a database transaction — if any step fails, no records are created.

After Import
------------

Once a campaign is imported:

1. View it under **TV Spots > Campaigns**
2. The origin ad unit and script rows are ready
3. Create adaptation ad units targeting specific markets (see :doc:`ad-units`)
4. Generate storyboards to visualize scripts (see :doc:`storyboards`)
