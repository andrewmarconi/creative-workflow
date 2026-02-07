# Reference Data Merge Documentation

## Overview

This document describes the merge of refined reference data files with existing data structures, preserving all required fields for the Django import system.

## Merge Date

2026-02-06

## Files Processed

### Input Files (Source Data)
- `data/new-regions.json` - Refined regions with country arrays
- `data/new-countries.json` - Refined countries with primary_language and languages arrays
- `data/new-languages.json` - Simple language code/name pairs
- `data/regions.json` (old) - Existing regions with insights, descriptions
- `data/countries.json` (old) - Existing countries with insights, notes
- `data/languages.json` (old) - Existing languages with model assignments, insights

### Output Files (Merged Data)
- `data/regions.json` - 20 regions
- `data/countries.json` - 92 countries
- `data/languages.json` - 74 languages
- `data/country_regions.json` - 192 country-region mappings
- `data/country_languages.json` - 123 country-language mappings

## Transformation Rules

### 1. regions.json
**Source**: `new-regions.json` + old `regions.json`

**Transformations**:
- Take `code`, `name` from new-regions.json
- Add `description` from old data (empty string if not found)
- Add `insights` array from old data (empty array if not found)
- Add `is_active: true` for all entries
- Output as flat array (not nested in "regions" key)

**Schema**:
```json
{
  "code": "string",
  "name": "string",
  "description": "string",
  "insights": [
    {
      "heading": "string",
      "points": ["string"]
    }
  ],
  "is_active": true
}
```

**Stats**:
- Total: 20 regions
- With insights: 4 (NA, LATAM, NORDICS, DACH)
- Without insights: 16

### 2. countries.json
**Source**: `new-countries.json` + old `countries.json`

**Transformations**:
- Take `code`, `name` from new-countries.json
- Rename `primary_language` → `default_language`
- Add `insights` array from old data (empty array if not found)
- Add `notes` from old data (empty string if not found)
- Add `is_active: true` for all entries

**Schema**:
```json
{
  "code": "string",
  "name": "string",
  "default_language": "string",
  "insights": [...],
  "notes": "string",
  "is_active": true
}
```

**Stats**:
- Total: 92 countries
- With insights: 11 (US, CA, FR, DE, etc.)
- Without insights: 81

### 3. languages.json
**Source**: `new-languages.json` + old `languages.json`

**Transformations**:
- Take `code`, `name` from new-languages.json
- Add `base_language` from old data, or derive from code (e.g., "en-US" → base: "en")
- Add `primary_model` from old data (default: "Qwen/Qwen2.5-7B-Instruct")
- Add `alternative_models` array from old data (empty array if not found)
- Add `insights` array from old data (empty array if not found)
- Add `notes` from old data (empty string if not found)
- Add `is_active: true` for all entries

**Schema**:
```json
{
  "code": "string",
  "name": "string",
  "base_language": "string",
  "primary_model": "string",
  "alternative_models": ["string"],
  "insights": [...],
  "notes": "string",
  "is_active": true
}
```

**Stats**:
- Total: 74 languages (all locale-specific with country codes)
- With insights: 12 (major language variants)
- Unique models: 3 (Qwen, microsoft/Phi, mistralai/Mistral)

### 4. country_regions.json
**Source**: Generated from `new-regions.json`

**Transformations**:
- For each region, extract its `countries` array
- Create mapping entry for each country code in the array
- Sort by country_code, then region_code

**Schema**:
```json
{
  "country_code": "string",
  "region_code": "string"
}
```

**Stats**:
- Total mappings: 192
- Countries in multiple regions: 67 (e.g., CA in NA and CANZUK)
- Average regions per country: 2.1
- Largest region: EMEA (53 countries)

### 5. country_languages.json
**Source**: Generated from `new-countries.json`

**Transformations**:
- For each country's `primary_language`, create mapping with `is_primary: true`
- For each entry in country's `languages` array, create mapping with `is_primary: false`
- Sort by country_code, then by is_primary (primary first), then language_code

**Schema**:
```json
{
  "country_code": "string",
  "language_code": "string",
  "is_primary": true|false
}
```

**Stats**:
- Total mappings: 123
- Primary language mappings: 92 (one per country)
- Secondary language mappings: 31
- Multilingual countries: 24 (e.g., IN with 6 languages)
- Monolingual countries: 68

## Validation

All output files have been validated for:
- ✓ Valid JSON array format
- ✓ All required fields present in every entry
- ✓ Field name changes applied correctly (primary_language → default_language)
- ✓ Cross-references are consistent (country codes exist, language codes exist)
- ✓ All entries have `is_active: true`
- ✓ Old data (insights, notes, descriptions) preserved where available

## Example: Canada (CA)

**Source Data**:
```json
// new-countries.json
{
  "code": "CA",
  "name": "Canada",
  "primary_language": "en-CA",
  "languages": ["fr-CA"]
}

// new-regions.json contains CA in:
// - NA (North America)
// - CANZUK
```

**Merged Result**:
```json
// countries.json
{
  "code": "CA",
  "name": "Canada",
  "default_language": "en-CA",
  "insights": [/* 3 sections from old data */],
  "notes": "",
  "is_active": true
}

// country_regions.json
[
  {"country_code": "CA", "region_code": "CANZUK"},
  {"country_code": "CA", "region_code": "NA"}
]

// country_languages.json
[
  {"country_code": "CA", "language_code": "en-CA", "is_primary": true},
  {"country_code": "CA", "language_code": "fr-CA", "is_primary": false}
]
```

## Next Steps

1. Review the generated files in `data/`
2. Import to database: `uv run manage.py import_reference_data`
3. Verify in Django admin that all data imported correctly

## Script

The merge was performed by `/Users/andrew/Develop/generative-creative-lab/merge_reference_data.py`, which can be re-run if needed:

```bash
python merge_reference_data.py
```

## Notes

- All 74 languages in the merged data are locale-specific (have country codes like en-US, fr-FR)
- No base languages without locale codes are present in new data
- Empty fields use appropriate defaults (empty string for notes/description, empty array for insights/alternative_models)
- All regions from new-regions.json are preserved in merged output
- Old data that doesn't exist in new data is not carried forward (only countries/regions/languages present in new data are in output)
