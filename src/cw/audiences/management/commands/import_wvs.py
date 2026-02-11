"""
Django management command to import World Values Survey data into Country insights.

Downloads the WVS dataset from Kaggle via kagglehub, parses country-level
cultural dimension profiles, and appends them as structured insight sections
to matching Country records.

Usage:
    uv run manage.py import_wvs                     # Download & import
    uv run manage.py import_wvs --dry-run            # Preview without importing
    uv run manage.py import_wvs --force-download      # Force re-download from Kaggle
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import kagglehub
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from cw.audiences.models import Country, WVSProfile
from cw.lib.wvs import WVS_HEADING_PREFIX, parse_wvs_csv, profile_to_insights

KAGGLE_DATASET = "fernandol/world-values-survey"
CSV_FILENAME = "WVS_per_Country.csv"
CODEBOOK_FILENAME = "Code_book.csv"
CODEBOOK_OUTPUT = Path(__file__).resolve().parents[5] / "data" / "wvs_codebook.json"


class Command(BaseCommand):
    help = "Import World Values Survey cultural profiles into Country insights"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying database",
        )
        parser.add_argument(
            "--force-download",
            action="store_true",
            help="Force re-download even if dataset is cached locally",
        )

    def handle(self, *args, **options):
        is_dry_run = options["dry_run"]
        force_download = options["force_download"]

        # Step 1: Download dataset
        self.stdout.write("=" * 60)
        self.stdout.write("Downloading World Values Survey dataset...")
        self.stdout.write("=" * 60)

        download_path = kagglehub.dataset_download(
            KAGGLE_DATASET,
            force_download=force_download,
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Dataset path: {download_path}")
        )

        # Step 2: Locate CSV
        csv_path = Path(download_path) / CSV_FILENAME
        if not csv_path.exists():
            # Try finding any CSV in the download directory
            csvs = list(Path(download_path).glob("*.csv"))
            if not csvs:
                self.stderr.write(
                    self.style.ERROR(
                        f"  No CSV files found in {download_path}"
                    )
                )
                return
            csv_path = csvs[0]
            self.stdout.write(
                self.style.WARNING(
                    f"  Expected {CSV_FILENAME} not found, using {csv_path.name}"
                )
            )

        # Step 3: Parse
        self.stdout.write(f"\n  Parsing {csv_path.name}...")
        profiles = parse_wvs_csv(str(csv_path))
        self.stdout.write(
            self.style.SUCCESS(
                f"  Parsed {len(profiles)} country profiles"
            )
        )

        # Step 4: Export codebook
        self._export_codebook(Path(download_path))

        # Step 5: Preview or import
        if is_dry_run:
            self._dry_run_preview(profiles)
        else:
            self._do_import(profiles)

    # Variables present in the WVS CSV but absent from Code_book.csv.
    # These are computed indices, WVS-specific variants of codebook variables,
    # or sparse supplementary questions.
    SUPPLEMENTARY_VARIABLES = {
        "TRADRAT5": {
            "label": "Traditional/Secular-Rational Values (Inglehart-Welzel index)",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y010": {
            "label": "Post-materialist index (4-item)",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y011": {
            "label": "Post-materialist index (12-item): materialist",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y012": {
            "label": "Post-materialist index (12-item): mixed",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y013": {
            "label": "Post-materialist index (12-item): post-materialist",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y014": {
            "label": "Post-materialist index (12-item): percentage index",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y020": {
            "label": "Autonomy index: obedience vs. independence (children)",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y021": {
            "label": "Autonomy index: autonomy",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y022": {
            "label": "Autonomy index: conformity",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y023": {
            "label": "Autonomy index: openness",
            "theme": "Special Indexes",
            "scale": "",
        },
        "Y024": {
            "label": "Autonomy index: self-direction",
            "theme": "Special Indexes",
            "scale": "",
        },
        "E179WVS": {
            "label": "Party preference: first choice (WVS-specific coding)",
            "theme": "Politics and Society",
            "scale": "",
        },
        "E180WVS": {
            "label": "Party preference: second choice (WVS-specific coding)",
            "theme": "Politics and Society",
            "scale": "",
        },
        "X025CSWVS": {
            "label": "Education, country-specific (WVS-specific coding)",
            "theme": "Socio-demographics",
            "scale": "",
        },
        "X048WVS": {
            "label": "Region of interview (WVS-specific coding)",
            "theme": "Socio-demographics",
            "scale": "",
        },
        "B030": {
            "label": "Trust in charitable/humanitarian organizations",
            "theme": "Perceptions of life",
            "scale": "1-4",
        },
        "B031": {
            "label": "Trust in universities",
            "theme": "Perceptions of life",
            "scale": "1-4",
        },
        "S007_01": {
            "label": "Unified respondent number",
            "theme": "Structure of the file",
            "scale": "",
        },
    }

    # Theme overrides for codebook entries that have misleading themes
    THEME_OVERRIDES = {
        "survself": "Special Indexes",
    }

    def _export_codebook(self, download_dir: Path):
        """Export WVS Code_book.csv as a JSON lookup file."""
        codebook_csv = download_dir / CODEBOOK_FILENAME
        if not codebook_csv.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"  {CODEBOOK_FILENAME} not found — skipping codebook export"
                )
            )
            return

        df = pd.read_csv(codebook_csv)
        codebook = {}
        for _, row in df.iterrows():
            var_code = row.get("Variable")
            if pd.isna(var_code):
                continue
            label = row.get("Label", "")
            theme = row.get("Theme", "")

            # Parse scale range from Categories (e.g. "1:Very important\n2:Rather...")
            scale = ""
            categories = row.get("Categories", "")
            if pd.notna(categories):
                codes = [
                    int(m.group(1))
                    for m in re.finditer(r"^(\d+):", str(categories), re.MULTILINE)
                ]
                if codes:
                    scale = f"{min(codes)}-{max(codes)}"

            var_key = str(var_code)
            codebook[var_key] = {
                "label": str(label) if pd.notna(label) else "",
                "theme": str(theme) if pd.notna(theme) else "",
                "scale": scale,
            }

            # Apply theme overrides
            if var_key in self.THEME_OVERRIDES:
                codebook[var_key]["theme"] = self.THEME_OVERRIDES[var_key]

        # Add supplementary variables not in Code_book.csv
        supplementary_added = 0
        for var_code, entry in self.SUPPLEMENTARY_VARIABLES.items():
            if var_code not in codebook:
                codebook[var_code] = entry
                supplementary_added += 1

        CODEBOOK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(CODEBOOK_OUTPUT, "w") as f:
            json.dump(codebook, f, indent=2, ensure_ascii=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Codebook exported: {len(codebook)} variables "
                f"({supplementary_added} supplementary) → {CODEBOOK_OUTPUT}"
            )
        )

    def _dry_run_preview(self, profiles):
        """Preview what would be imported without modifying database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        self.stdout.write("=" * 60)

        # Check which profiles match existing countries
        existing_codes = set(
            Country.objects.values_list("code", flat=True)
        )

        matched = []
        skipped = []
        for profile in profiles:
            if profile.iso_alpha2 in existing_codes:
                matched.append(profile)
            else:
                skipped.append(profile)

        self.stdout.write(f"\n  Countries to update: {len(matched)}")
        for p in matched[:10]:
            insights = profile_to_insights(p)
            section_count = len(insights)
            point_count = sum(len(s["points"]) for s in insights)
            self.stdout.write(
                f"    {p.iso_alpha2} ({p.country_name}) — "
                f"Wave {p.wave}, {section_count} sections, "
                f"{point_count} insight points"
            )
        if len(matched) > 10:
            self.stdout.write(f"    ... and {len(matched) - 10} more")

        if skipped:
            self.stdout.write(f"\n  Countries not in database (will skip): {len(skipped)}")
            for p in skipped[:5]:
                self.stdout.write(f"    {p.iso_alpha2} ({p.country_name})")
            if len(skipped) > 5:
                self.stdout.write(f"    ... and {len(skipped) - 5} more")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.WARNING("Run without --dry-run to apply changes")
        )
        self.stdout.write("=" * 60)

    @transaction.atomic
    def _do_import(self, profiles):
        """Import WVS insights and raw profiles into the database."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Importing WVS data into Country records...")
        self.stdout.write("=" * 60)

        insights_updated = 0
        profiles_saved = 0
        skipped_count = 0

        for profile in profiles:
            try:
                country = Country.objects.get(code=profile.iso_alpha2)
            except Country.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping {profile.country_name} "
                        f"({profile.iso_alpha2}): not in database"
                    )
                )
                skipped_count += 1
                continue

            # 1. Update narrative insights on Country
            existing_insights = country.insights or []
            non_wvs = [
                s
                for s in existing_insights
                if not s.get("heading", "").startswith(WVS_HEADING_PREFIX)
            ]

            wvs_sections = profile_to_insights(profile)
            if wvs_sections:
                country.insights = non_wvs + wvs_sections
                country.save(update_fields=["insights", "updated_at"])
                insights_updated += 1

            # 2. Save raw WVS data for dynamic theme-based lookups
            if profile.raw_data:
                WVSProfile.objects.update_or_create(
                    country=country,
                    wave=profile.wave,
                    defaults={"raw_data": profile.raw_data},
                )
                profiles_saved += 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Complete!"))
        self.stdout.write(f"  Country insights updated: {insights_updated}")
        self.stdout.write(f"  WVS raw profiles saved: {profiles_saved}")
        self.stdout.write(f"  Countries skipped: {skipped_count}")
        self.stdout.write(f"  Total WVS profiles parsed: {len(profiles)}")
        self.stdout.write("=" * 60)
