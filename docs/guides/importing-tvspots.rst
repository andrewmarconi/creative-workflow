Importing TV Spots
==================

TV spots can be imported from JSON files using the ``import_tvspot`` management command. This guide covers the JSON format and import process.

JSON Format
-----------

TV spot JSON files follow a two-column AV script format with metadata. Here's the structure:

Required Fields
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``client_name``
     - string
     - Client or company name
   * - ``script_title``
     - string
     - Title of the TV spot script
   * - ``total_runtime_seconds``
     - integer
     - Total runtime in seconds (typically 15, 30, 60, 90)
   * - ``job_id``
     - string
     - Unique internal project identifier (e.g., "ACME-2024-001")
   * - ``script_rows``
     - array
     - Array of script row objects (at least one required)

Optional Fields
^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``brand_name``
     - string
     - Brand name (if different from client)
   * - ``language``
     - string
     - Language code for origin version (default: "en-US")
   * - ``notes``
     - string
     - Additional notes about the spot

Script Row Fields
^^^^^^^^^^^^^^^^^

Each object in ``script_rows`` represents one row in the two-column AV script:

.. list-table::
   :header-rows: 1
   :widths: 20 15 10 55

   * - Field
     - Type
     - Required
     - Description
   * - ``visual_text``
     - string
     - Yes
     - Left column: visuals, shots, graphics, supers, VFX, locations
   * - ``audio_text``
     - string
     - Yes
     - Right column: VO, dialogue, SFX, music cues, taglines
   * - ``shot_number``
     - string
     - No
     - Shot identifier (e.g., "01", "1A", "MONT-01"). Auto-generated if omitted.
   * - ``timecode_start``
     - string
     - No
     - Start timecode (e.g., "00:00:05:00" or "5.0")
   * - ``duration_seconds``
     - number
     - No
     - Row duration in seconds (e.g., 2.5)

Example JSON
------------

A complete 30-second TV spot example is provided at ``data/example_tvspot.json``:

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
       }
     ]
   }

Importing
---------

Validate First (Dry Run)
^^^^^^^^^^^^^^^^^^^^^^^^

Always validate your JSON before importing:

.. code-block:: bash

   uv run manage.py import_tvspot path/to/spot.json --dry-run

This checks:

- All required fields are present
- ``job_id`` is unique (not already in database)
- Each script row has ``visual_text`` and ``audio_text``
- ``total_runtime_seconds`` is a positive integer

Import the TV Spot
^^^^^^^^^^^^^^^^^^

Once validation passes:

.. code-block:: bash

   uv run manage.py import_tvspot path/to/spot.json

What Gets Created
^^^^^^^^^^^^^^^^^

On successful import:

1. **TvSpot** record with metadata fields
2. **TvSpotVersion** (origin) with:

   - ``version_type``: "origin"
   - ``code``: "ORIGIN"
   - ``name``: "Origin"
   - ``language``: From JSON or default "en-US"

3. **TvSpotScriptRow** for each item in ``script_rows``:

   - ``order_index``: 0-indexed position in array
   - ``shot_number``: From JSON or auto-generated ("01", "02", ...)

The import is atomic—if any step fails, the entire transaction is rolled back.

Writing Visual Descriptions
---------------------------

For best results with storyboard generation, write visual descriptions that include:

- **Shot type**: Wide, medium, close-up, extreme close-up
- **Camera movement**: Pan, tilt, dolly, tracking, static
- **Lighting**: Natural, dramatic, soft, high-key, low-key
- **Subject details**: Age, appearance, clothing, expression
- **Environment**: Location, time of day, weather, atmosphere
- **Action**: What's happening in the frame
- **Graphics**: Supers, lower thirds, logos, legal copy

Example:

.. code-block:: text

   Close-up: TALENT (30s, professional woman) takes first sip of coffee.
   Expression transforms from tired to pleasantly surprised. Soft morning
   light from window, shallow depth of field. Steam rises from cup.

Next Steps
----------

After importing a TV spot:

1. View it in Django admin under **TV Spots**
2. Create market adaptations for localization
3. Generate storyboards using diffusion models

See the :doc:`../api/tvspots` documentation for programmatic access.
