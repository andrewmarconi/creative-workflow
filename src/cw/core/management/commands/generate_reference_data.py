"""
Generate comprehensive Country and Language reference data from Babel CLDR.

Reads existing JSON files from data/ to preserve manually-curated insights,
notes, and model assignments. Generates new entries from Babel for missing
countries and languages. Writes merged data back to JSON files for review
before import via import_reference_data.

Usage:
    uv run manage.py generate_reference_data                       # Generate to data/
    uv run manage.py generate_reference_data --dry-run             # Preview changes
    uv run manage.py generate_reference_data --min-population 10   # Higher threshold
    uv run manage.py generate_reference_data --dir staging/        # Custom output dir
"""

import json
from pathlib import Path

from babel import Locale, UnknownLocaleError
from babel.languages import get_official_languages, get_territory_language_info
from django.core.management.base import BaseCommand

DEFAULT_PRIMARY_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_ALTERNATIVE_MODELS = ["CohereForAI/aya-expanse-8b"]

# Meta-territories and non-country codes to exclude
META_TERRITORIES = {
    "EU", "EZ", "UN", "QO",  # Supranational
    "XA", "XB", "ZZ",        # Unknown/private use
    "AC", "BV", "CP", "HM",  # Uninhabited territories
    "TF", "AQ", "TA",        # Antarctica, remote islands
}

STATUS_WEIGHT = {
    "official": 3,
    "de_facto_official": 2,
    "official_regional": 1,
    None: 0,
}


class Command(BaseCommand):
    help = "Generate Country and Language reference data from Babel CLDR"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="data",
            help="Output directory for JSON files (default: data/)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing files",
        )
        parser.add_argument(
            "--min-population",
            type=float,
            default=5.0,
            help="Minimum population %% for language inclusion (default: 5.0)",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["dir"])
        is_dry_run = options["dry_run"]
        min_population = options["min_population"]

        self.stdout.write("=" * 60)
        self.stdout.write("Generating reference data from Babel CLDR")
        self.stdout.write("=" * 60)

        # Phase 1: Load existing data
        existing = self._load_existing_data(output_dir)

        # Phase 2: Generate from Babel
        en = Locale("en")
        territory_codes = sorted(
            c for c in en.territories
            if len(c) == 2 and c.isalpha() and c not in META_TERRITORIES
        )

        countries, languages, mappings, stats = self._generate_all(
            territory_codes, en, existing, min_population
        )

        # Phase 3: Preview or write
        if is_dry_run:
            self._dry_run_preview(countries, languages, mappings, stats, existing)
        else:
            self._write_output(output_dir, countries, languages, mappings, stats, existing)

    def _load_existing_data(self, input_dir: Path) -> dict:
        """Load existing JSON files and index by code."""
        existing = {
            "countries": {},
            "languages": {},
            "country_languages": set(),
            "country_languages_list": [],
        }

        files = {
            "countries": "countries.json",
            "languages": "languages.json",
            "country_languages": "country_languages.json",
        }

        for key, filename in files.items():
            file_path = input_dir / filename
            if not file_path.exists():
                self.stdout.write(self.style.WARNING(f"  {filename} not found, starting fresh"))
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING(f"  {filename} invalid, starting fresh"))
                continue

            if key == "countries":
                existing["countries"] = {c["code"]: c for c in data}
            elif key == "languages":
                existing["languages"] = {lang["code"]: lang for lang in data}
            elif key == "country_languages":
                existing["country_languages"] = {
                    (m["country_code"], m["language_code"]) for m in data
                }
                existing["country_languages_list"] = data

            self.stdout.write(f"  ✓ Loaded {filename}: {len(data)} records")

        return existing

    def _generate_all(self, territory_codes, en, existing, min_population):
        """Generate countries, languages, and mappings from Babel."""
        countries = {}
        languages = {}
        mappings = []
        stats = {
            "countries_preserved": 0,
            "countries_new": 0,
            "languages_preserved": 0,
            "languages_new": 0,
            "mappings_preserved": 0,
            "mappings_new": 0,
            "default_lang_filled": [],
        }

        # Generate countries and their languages
        for territory in territory_codes:
            territory_name = en.territories.get(territory, territory)

            # Build country entry
            if territory in existing["countries"]:
                country = dict(existing["countries"][territory])
                country["name"] = territory_name  # Update name from Babel
                stats["countries_preserved"] += 1
            else:
                country = {
                    "code": territory,
                    "name": territory_name,
                    "default_language": None,
                    "insights": [],
                    "notes": "",
                    "is_active": False,
                }
                stats["countries_new"] += 1

            countries[territory] = country

            # Get official languages for this territory
            try:
                official_langs = get_official_languages(
                    territory, regional=True, de_facto=True
                )
                lang_info = get_territory_language_info(territory)
            except Exception:
                continue

            if not official_langs:
                continue

            # Process languages, tracking best candidate for default_language
            seen_base = set()
            territory_lang_entries = []

            for babel_lang in official_langs:
                details = lang_info.get(babel_lang, {})
                pop = details.get("population_percent", 0)
                status = details.get("official_status")

                # Filter: official/de_facto always included, regional only if >= threshold
                if status not in ("official", "de_facto_official") and pop < min_population:
                    continue

                # Strip script subtag to build BCP47 code
                base_lang = babel_lang.split("_")[0]
                if base_lang in seen_base:
                    continue  # Skip script-variant duplicates (e.g., sr vs sr_Latn)
                seen_base.add(base_lang)

                bcp47_code = f"{base_lang}-{territory}"
                display_name = self._get_display_name(babel_lang, territory, en)

                # Build language entry
                if bcp47_code in existing["languages"]:
                    lang_entry = dict(existing["languages"][bcp47_code])
                    lang_entry["name"] = display_name
                    stats["languages_preserved"] += 1
                elif bcp47_code not in languages:
                    lang_entry = {
                        "code": bcp47_code,
                        "name": display_name,
                        "base_language": base_lang,
                        "primary_model": DEFAULT_PRIMARY_MODEL,
                        "alternative_models": list(DEFAULT_ALTERNATIVE_MODELS),
                        "insights": [],
                        "notes": "",
                        "is_active": False,
                    }
                    stats["languages_new"] += 1
                else:
                    lang_entry = languages[bcp47_code]

                languages[bcp47_code] = lang_entry

                territory_lang_entries.append({
                    "bcp47_code": bcp47_code,
                    "population_percent": pop,
                    "official_status": status,
                })

            # Determine primary language and create mappings
            if territory_lang_entries:
                ranked = sorted(
                    territory_lang_entries,
                    key=lambda e: (
                        STATUS_WEIGHT.get(e["official_status"], 0),
                        e["population_percent"],
                    ),
                    reverse=True,
                )
                primary_code = ranked[0]["bcp47_code"]

                # Fill default_language if not set
                if not country.get("default_language"):
                    country["default_language"] = primary_code
                    if territory in existing["countries"]:
                        stats["default_lang_filled"].append(territory)

                for entry in ranked:
                    pair = (territory, entry["bcp47_code"])
                    is_primary = entry["bcp47_code"] == primary_code

                    # Preserve existing mapping's is_primary flag
                    if pair in existing["country_languages"]:
                        # Find the existing mapping to preserve its is_primary
                        existing_mapping = next(
                            (m for m in existing["country_languages_list"]
                             if m["country_code"] == territory
                             and m["language_code"] == entry["bcp47_code"]),
                            None,
                        )
                        if existing_mapping:
                            is_primary = existing_mapping["is_primary"]
                        stats["mappings_preserved"] += 1
                    else:
                        stats["mappings_new"] += 1

                    mappings.append({
                        "country_code": territory,
                        "language_code": entry["bcp47_code"],
                        "is_primary": is_primary,
                    })

        # Preserve existing languages not generated by Babel
        for code, lang in existing["languages"].items():
            if code not in languages:
                languages[code] = dict(lang)

        # Preserve existing country-language mappings not regenerated
        existing_mapping_pairs = {(m["country_code"], m["language_code"]) for m in mappings}
        for m in existing["country_languages_list"]:
            pair = (m["country_code"], m["language_code"])
            if pair not in existing_mapping_pairs:
                mappings.append(dict(m))
                stats["mappings_preserved"] += 1

        return countries, languages, mappings, stats

    def _get_display_name(self, babel_lang_code, territory, en):
        """Get display name for a language-territory pair."""
        # Try parsing as a full locale first
        try:
            locale = Locale.parse(f"{babel_lang_code}_{territory}")
            name = locale.get_display_name("en")
            if name:
                return name
        except (UnknownLocaleError, ValueError):
            pass

        # Fallback: compose from components
        base_lang = babel_lang_code.split("_")[0]
        lang_name = en.languages.get(base_lang, base_lang)
        territory_name = en.territories.get(territory, territory)
        return f"{lang_name} ({territory_name})"

    def _dry_run_preview(self, countries, languages, mappings, stats, existing):
        """Print preview of what would be generated."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No files will be written"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"\nSources:")
        self.stdout.write(f"  Existing: {len(existing['countries'])} countries, "
                          f"{len(existing['languages'])} languages, "
                          f"{len(existing['country_languages'])} mappings")
        self.stdout.write(f"  Babel CLDR: {len(countries)} territories")

        self.stdout.write(f"\nCountries:")
        self.stdout.write(f"  Preserved: {stats['countries_preserved']}")
        self.stdout.write(f"  New (is_active=false): {stats['countries_new']}")
        self.stdout.write(f"  Total: {len(countries)}")

        self.stdout.write(f"\nLanguages:")
        self.stdout.write(f"  Preserved: {stats['languages_preserved']}")
        self.stdout.write(f"  New (is_active=false): {stats['languages_new']}")
        self.stdout.write(f"  Total: {len(languages)}")

        self.stdout.write(f"\nCountry-Language Mappings:")
        self.stdout.write(f"  Preserved: {stats['mappings_preserved']}")
        self.stdout.write(f"  New: {stats['mappings_new']}")
        self.stdout.write(f"  Total: {len(mappings)}")

        if stats["default_lang_filled"]:
            self.stdout.write(f"\nCountries with default_language filled:")
            for code in stats["default_lang_filled"]:
                country = countries[code]
                self.stdout.write(f"  {code} ({country['name']}): {country['default_language']}")

        # Show sample new countries
        new_countries = [c for c in countries.values() if not c.get("is_active", True) and c["code"] not in existing["countries"]]
        if new_countries:
            self.stdout.write(f"\nSample new countries:")
            for c in new_countries[:5]:
                self.stdout.write(f"  - {c['code']}: {c['name']} (default: {c.get('default_language', 'None')})")
            if len(new_countries) > 5:
                self.stdout.write(f"  ... and {len(new_countries) - 5} more")

        # Show sample new languages
        new_langs = [lang for lang in languages.values() if lang["code"] not in existing["languages"]]
        if new_langs:
            self.stdout.write(f"\nSample new languages:")
            for lang in new_langs[:5]:
                self.stdout.write(f"  - {lang['code']}: {lang['name']}")
            if len(new_langs) > 5:
                self.stdout.write(f"  ... and {len(new_langs) - 5} more")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("Run without --dry-run to write files"))
        self.stdout.write("=" * 60)

    def _write_output(self, output_dir, countries, languages, mappings, stats, existing):
        """Write merged data to JSON files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Sort by code for stable output
        countries_list = sorted(countries.values(), key=lambda c: c["code"])
        languages_list = sorted(languages.values(), key=lambda lang: lang["code"])
        mappings_list = sorted(mappings, key=lambda m: (m["country_code"], m["language_code"]))

        files = {
            "countries.json": countries_list,
            "languages.json": languages_list,
            "country_languages.json": mappings_list,
        }

        self.stdout.write("\nWriting files:")
        for filename, data in files.items():
            file_path = output_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"  ✓ {filename}: {len(data)} records")

        # Print summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Generation Complete!"))
        self.stdout.write(f"  Countries: {stats['countries_preserved']} preserved + "
                          f"{stats['countries_new']} new = {len(countries_list)}")
        self.stdout.write(f"  Languages: {stats['languages_preserved']} preserved + "
                          f"{stats['languages_new']} new = {len(languages_list)}")
        self.stdout.write(f"  Mappings: {stats['mappings_preserved']} preserved + "
                          f"{stats['mappings_new']} new = {len(mappings_list)}")

        if stats["default_lang_filled"]:
            self.stdout.write(f"  Default language filled for: {', '.join(stats['default_lang_filled'])}")

        self.stdout.write(f"\nNext steps:")
        self.stdout.write(f"  1. Review changes: git diff {output_dir}/")
        self.stdout.write(f"  2. Import to database: uv run manage.py import_reference_data")
        self.stdout.write("=" * 60)
