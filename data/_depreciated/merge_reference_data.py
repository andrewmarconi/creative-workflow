#!/usr/bin/env python3
"""
Merge refined reference data files with existing data structures.
Preserves all required fields for the Django import system.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Base paths
DATA_DIR = Path(__file__).parent / "data"

def load_json(filename: str) -> Any:
    """Load JSON file from data directory."""
    with open(DATA_DIR / filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filename: str, data: Any):
    """Save data to JSON file in data directory."""
    with open(DATA_DIR / filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Created {filename}")

def determine_base_language(code: str) -> str:
    """Determine base language from locale-specific code."""
    if '-' in code:
        return code.split('-')[0]
    return ""

def merge_regions():
    """Merge new-regions.json with existing regions.json."""
    print("\n1. Processing regions.json...")

    # Load source files
    new_regions = load_json("new-regions.json")
    try:
        old_regions = load_json("regions.json")
        old_regions_map = {r["code"]: r for r in old_regions}
    except FileNotFoundError:
        old_regions_map = {}

    # Build merged regions
    merged = []
    for region in new_regions["regions"]:
        code = region["code"]
        old_data = old_regions_map.get(code, {})

        merged_region = {
            "code": code,
            "name": region["name"],
            "description": old_data.get("description", ""),
            "insights": old_data.get("insights", []),
            "is_active": True
        }
        merged.append(merged_region)

    save_json("regions.json", merged)
    return merged

def merge_countries():
    """Merge new-countries.json with existing countries.json."""
    print("\n2. Processing countries.json...")

    # Load source files
    new_countries = load_json("new-countries.json")
    try:
        old_countries = load_json("countries.json")
        old_countries_map = {c["code"]: c for c in old_countries}
    except FileNotFoundError:
        old_countries_map = {}

    # Build merged countries
    merged = []
    for country in new_countries["countries"]:
        code = country["code"]
        old_data = old_countries_map.get(code, {})

        merged_country = {
            "code": code,
            "name": country["name"],
            "default_language": country["primary_language"],  # Renamed field
            "insights": old_data.get("insights", []),
            "notes": old_data.get("notes", ""),
            "is_active": True
        }
        merged.append(merged_country)

    save_json("countries.json", merged)
    return merged

def merge_languages():
    """Merge new-languages.json with existing languages.json."""
    print("\n3. Processing languages.json...")

    # Load source files
    new_languages = load_json("new-languages.json")
    try:
        old_languages = load_json("languages.json")
        old_languages_map = {l["code"]: l for l in old_languages}
    except FileNotFoundError:
        old_languages_map = {}

    # Default model for languages without existing data
    DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

    # Build merged languages
    merged = []
    for language in new_languages["languages"]:
        code = language["code"]
        old_data = old_languages_map.get(code, {})

        merged_language = {
            "code": code,
            "name": language["name"],
            "base_language": old_data.get("base_language", determine_base_language(code)),
            "primary_model": old_data.get("primary_model", DEFAULT_MODEL),
            "alternative_models": old_data.get("alternative_models", []),
            "insights": old_data.get("insights", []),
            "notes": old_data.get("notes", ""),
            "is_active": True
        }
        merged.append(merged_language)

    save_json("languages.json", merged)
    return merged

def generate_country_regions():
    """Generate country_regions.json from new-regions.json."""
    print("\n4. Processing country_regions.json...")

    # Load source file
    new_regions = load_json("new-regions.json")

    # Build country-region mappings
    mappings = []
    for region in new_regions["regions"]:
        region_code = region["code"]
        for country_code in region["countries"]:
            mappings.append({
                "country_code": country_code,
                "region_code": region_code
            })

    # Sort by country code for consistency
    mappings.sort(key=lambda x: (x["country_code"], x["region_code"]))

    save_json("country_regions.json", mappings)
    return mappings

def generate_country_languages():
    """Generate country_languages.json from new-countries.json."""
    print("\n5. Processing country_languages.json...")

    # Load source file
    new_countries = load_json("new-countries.json")

    # Build country-language mappings
    mappings = []
    for country in new_countries["countries"]:
        country_code = country["code"]

        # Add primary language
        mappings.append({
            "country_code": country_code,
            "language_code": country["primary_language"],
            "is_primary": True
        })

        # Add additional languages
        for language_code in country.get("languages", []):
            mappings.append({
                "country_code": country_code,
                "language_code": language_code,
                "is_primary": False
            })

    # Sort by country code and primary status
    mappings.sort(key=lambda x: (x["country_code"], not x["is_primary"], x["language_code"]))

    save_json("country_languages.json", mappings)
    return mappings

def verify_output_files():
    """Verify all output files were created and have valid structure."""
    print("\n6. Verifying output files...")

    required_files = [
        "regions.json",
        "countries.json",
        "languages.json",
        "country_regions.json",
        "country_languages.json"
    ]

    for filename in required_files:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"✗ Missing: {filename}")
            continue

        try:
            data = load_json(filename)
            if not isinstance(data, list):
                print(f"✗ Invalid format (not array): {filename}")
                continue

            if len(data) == 0:
                print(f"⚠ Empty file: {filename}")
            else:
                print(f"✓ Valid: {filename} ({len(data)} entries)")

        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {filename} - {e}")

def main():
    """Main entry point."""
    print("=" * 60)
    print("Merging Reference Data Files")
    print("=" * 60)

    try:
        # Process each file type
        merge_regions()
        merge_countries()
        merge_languages()
        generate_country_regions()
        generate_country_languages()

        # Verify outputs
        verify_output_files()

        print("\n" + "=" * 60)
        print("✓ Merge completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the generated files in data/")
        print("2. Run: uv run manage.py import_reference_data")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
