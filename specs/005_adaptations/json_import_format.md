# JSON Import Format for TV Spots

## Overview

This document defines the JSON schema for importing TV spots via the `import_tvspot` management command or admin action.

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["client_name", "script_title", "total_runtime_seconds", "job_id", "script_rows"],
  "properties": {
    "client_name": {
      "type": "string",
      "description": "Client/company name",
      "minLength": 1,
      "maxLength": 255
    },
    "brand_name": {
      "type": "string",
      "description": "Brand name (optional)",
      "maxLength": 255
    },
    "script_title": {
      "type": "string",
      "description": "Title of the TV spot script",
      "minLength": 1,
      "maxLength": 255
    },
    "total_runtime_seconds": {
      "type": "integer",
      "description": "Total runtime in seconds (typically 15, 30, 60, 90)",
      "minimum": 1
    },
    "job_id": {
      "type": "string",
      "description": "Unique internal project identifier",
      "minLength": 1,
      "maxLength": 100,
      "pattern": "^[A-Za-z0-9_-]+$"
    },
    "language": {
      "type": "string",
      "description": "Language code for the origin version (default: en-US)",
      "default": "en-US"
    },
    "notes": {
      "type": "string",
      "description": "Optional notes about the spot"
    },
    "script_rows": {
      "type": "array",
      "description": "Script rows in order",
      "minItems": 1,
      "items": {
        "$ref": "#/definitions/script_row"
      }
    }
  },
  "definitions": {
    "script_row": {
      "type": "object",
      "required": ["visual_text", "audio_text"],
      "properties": {
        "shot_number": {
          "type": "string",
          "description": "Shot identifier (e.g., '01', '1A', 'MONT-01')",
          "maxLength": 20
        },
        "timecode_start": {
          "type": "string",
          "description": "Start timecode (e.g., '00:00:05:00' or '5.0')",
          "maxLength": 12
        },
        "duration_seconds": {
          "type": "number",
          "description": "Row duration in seconds",
          "minimum": 0
        },
        "visual_text": {
          "type": "string",
          "description": "Visual column: shots, graphics, supers, VFX, locations",
          "minLength": 1
        },
        "audio_text": {
          "type": "string",
          "description": "Audio column: VO, dialogue, SFX, music cues, taglines",
          "minLength": 1
        }
      }
    }
  }
}
```

## Example

```json
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
      "visual_text": "Close-up: TALENT drinks. Expression transforms from tired to energized. Eyes brighten.",
      "audio_text": "VO: \"Acme Energy. The boost you need.\"\nMUSIC: Peak energy"
    },
    {
      "shot_number": "04",
      "timecode_start": "00:00:10:00",
      "duration_seconds": 5.0,
      "visual_text": "Montage: TALENT moving through morning routine with energy - shower, getting dressed, grabbing bag. Quick cuts, dynamic movement.",
      "audio_text": "MUSIC: Upbeat, driving tempo\nSFX: Quick whoosh transitions"
    },
    {
      "shot_number": "05",
      "timecode_start": "00:00:15:00",
      "duration_seconds": 4.0,
      "visual_text": "Wide shot: City street. TALENT walks confidently to work, passing others who look tired. TALENT smiles, energetic stride.",
      "audio_text": "VO: \"Start your day the Acme way.\"\nMUSIC: Continues upbeat"
    },
    {
      "shot_number": "06",
      "timecode_start": "00:00:19:00",
      "duration_seconds": 3.0,
      "visual_text": "Medium shot: Office environment. TALENT enters, greets colleagues enthusiastically. Others react positively.",
      "audio_text": "SFX: Office ambience, greetings\nMUSIC: Settling to confident tone"
    },
    {
      "shot_number": "07",
      "timecode_start": "00:00:22:00",
      "duration_seconds": 5.0,
      "visual_text": "Product shot: ACME ENERGY DRINK can on desk, office in soft focus behind. Logo prominent.\nSUPER: \"ACME ENERGY - BOOST YOUR MORNING\"\nSUPER: \"Available everywhere\"",
      "audio_text": "VO: \"Acme Energy. Available everywhere.\"\nMUSIC: Resolve to tagline sting"
    },
    {
      "shot_number": "08",
      "timecode_start": "00:00:27:00",
      "duration_seconds": 3.0,
      "visual_text": "End card: ACME logo center frame, product can beside it.\nSUPER: \"acme-energy.com\"\nLEGAL: \"Drink responsibly. Not for children under 16.\"",
      "audio_text": "MUSIC: Final tag\nSFX: Subtle energy whoosh"
    }
  ]
}
```

## Validation Rules

### Required Fields
- `client_name`: Non-empty string
- `script_title`: Non-empty string
- `total_runtime_seconds`: Positive integer
- `job_id`: Unique identifier (checked against database)
- `script_rows`: At least one row

### Script Row Validation
- `visual_text`: Required, non-empty
- `audio_text`: Required, non-empty
- `shot_number`: Optional, auto-generated if missing (01, 02, 03...)
- `duration_seconds`: Optional, if provided must be >= 0

### Uniqueness
- `job_id` must be unique across all `TvSpot` records
- Import will fail if `job_id` already exists (use update endpoint for modifications)

## Import Behavior

### On Success
1. Creates `TvSpot` with metadata fields
2. Creates `TvSpotVersion` with:
   - `version_type`: "origin"
   - `code`: "ORIGIN"
   - `name`: "Origin"
   - `language`: From JSON or default "en-US"
3. Creates `TvSpotScriptRow` for each item in `script_rows`:
   - `order_index`: 0-indexed position in array
   - `shot_number`: From JSON or auto-generated

### On Failure
- Transaction is rolled back (no partial imports)
- Error message includes specific validation failures

## CLI Usage

```bash
# Import from file
uv run manage.py import_tvspot path/to/spot.json

# Import with verbose output
uv run manage.py import_tvspot path/to/spot.json --verbosity=2

# Dry run (validate only, don't create records)
uv run manage.py import_tvspot path/to/spot.json --dry-run
```

## Admin Usage

1. Navigate to TV Spots list in Django admin
2. Click "Import TV Spot" button
3. Paste JSON into textarea
4. Click "Validate" to check for errors
5. Click "Import" to create records
