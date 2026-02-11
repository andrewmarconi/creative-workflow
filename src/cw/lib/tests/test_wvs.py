"""Unit tests for WVS parser module.

These tests verify the pure data transformation logic without requiring
a database connection or Kaggle download.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from cw.lib.wvs import (
    ALL_DIMENSION_COLS,
    WVS_COUNTRY_TO_ISO,
    WVS_HEADING_PREFIX,
    WVSCountryProfile,
    _interpret_civic,
    _interpret_gender,
    _interpret_life_satisfaction,
    _interpret_religion,
    _interpret_tolerance,
    _interpret_trad_secular,
    _interpret_trust,
    _interpret_surv_selfexp,
    parse_wvs_csv,
    profile_to_insights,
)


# ---------------------------------------------------------------------------
# Country code mapping tests
# ---------------------------------------------------------------------------


class TestCountryCodeMapping:
    """Tests for WVS_COUNTRY_TO_ISO mapping."""

    def test_major_countries_mapped(self):
        assert WVS_COUNTRY_TO_ISO["United States"] == "US"
        assert WVS_COUNTRY_TO_ISO["Japan"] == "JP"
        assert WVS_COUNTRY_TO_ISO["Sweden"] == "SE"
        assert WVS_COUNTRY_TO_ISO["Brazil"] == "BR"
        assert WVS_COUNTRY_TO_ISO["Nigeria"] == "NG"
        assert WVS_COUNTRY_TO_ISO["Germany"] == "DE"
        assert WVS_COUNTRY_TO_ISO["India"] == "IN"
        assert WVS_COUNTRY_TO_ISO["China"] == "CN"

    def test_edge_case_names(self):
        """WVS uses non-standard names for some countries."""
        assert WVS_COUNTRY_TO_ISO["Great Britain"] == "GB"
        assert WVS_COUNTRY_TO_ISO["Czech Rep."] == "CZ"
        assert WVS_COUNTRY_TO_ISO["Dominican Rep."] == "DO"
        assert WVS_COUNTRY_TO_ISO["Cyprus (G)"] == "CY"
        assert WVS_COUNTRY_TO_ISO["Viet Nam"] == "VN"
        assert WVS_COUNTRY_TO_ISO["South Korea"] == "KR"

    def test_bosnia_variants_map_to_same_code(self):
        assert WVS_COUNTRY_TO_ISO["Bosnia"] == "BA"
        assert WVS_COUNTRY_TO_ISO["Bosnian Federation"] == "BA"

    def test_all_values_are_two_letter_codes(self):
        for country, code in WVS_COUNTRY_TO_ISO.items():
            assert len(code) == 2, f"{country} has invalid code: {code}"
            assert code == code.upper(), f"{country} code not uppercase: {code}"

    def test_unknown_country_not_in_mapping(self):
        assert "Atlantis" not in WVS_COUNTRY_TO_ISO


# ---------------------------------------------------------------------------
# Score interpretation tests
# ---------------------------------------------------------------------------


class TestInterpretTradSecular:
    def test_strongly_secular(self):
        result = _interpret_trad_secular(1.5)
        assert result is not None
        assert "Strongly secular-rational" in result
        assert "1.50" in result

    def test_moderately_secular(self):
        result = _interpret_trad_secular(0.7)
        assert "Moderately secular-rational" in result

    def test_mixed(self):
        result = _interpret_trad_secular(0.0)
        assert "Mixed traditional and secular" in result

    def test_strongly_traditional(self):
        result = _interpret_trad_secular(-1.0)
        assert "Strongly traditional" in result

    def test_none_returns_none(self):
        assert _interpret_trad_secular(None) is None


class TestInterpretSurvSelfexp:
    def test_strong_self_expression(self):
        result = _interpret_surv_selfexp(1.5)
        assert "Strong self-expression" in result

    def test_moderate_self_expression(self):
        result = _interpret_surv_selfexp(0.7)
        assert "Moderate self-expression" in result

    def test_transitional(self):
        result = _interpret_surv_selfexp(0.0)
        assert "Transitional" in result

    def test_strong_survival(self):
        result = _interpret_surv_selfexp(-1.0)
        assert "Strong survival" in result

    def test_none_returns_none(self):
        assert _interpret_surv_selfexp(None) is None


class TestInterpretTrust:
    def test_high_trust(self):
        # Score of 1.3 means 70% trust
        result = _interpret_trust(1.3)
        assert "High social trust" in result
        assert "70%" in result

    def test_moderate_trust(self):
        result = _interpret_trust(1.5)
        assert "Moderate social trust" in result
        assert "50%" in result

    def test_low_trust(self):
        result = _interpret_trust(1.7)
        assert "Low social trust" in result
        assert "30%" in result

    def test_very_low_trust(self):
        result = _interpret_trust(1.9)
        assert "Very low social trust" in result

    def test_none_returns_none(self):
        assert _interpret_trust(None) is None


class TestInterpretReligion:
    def test_very_important_god(self):
        result = _interpret_religion(None, 9.0)
        assert "very important" in result

    def test_moderate_god(self):
        result = _interpret_religion(None, 6.0)
        assert "moderate importance" in result

    def test_unimportant_god(self):
        result = _interpret_religion(None, 3.0)
        assert "relatively unimportant" in result

    def test_religion_core_priority(self):
        result = _interpret_religion(1.2, None)
        assert "core life priority" in result

    def test_religion_peripheral(self):
        result = _interpret_religion(3.5, None)
        assert "peripheral" in result

    def test_both_none_returns_none(self):
        assert _interpret_religion(None, None) is None


class TestInterpretTolerance:
    def test_high_tolerance(self):
        result = _interpret_tolerance(8.0)
        assert "High social tolerance" in result

    def test_moderate_tolerance(self):
        result = _interpret_tolerance(5.5)
        assert "Moderate social tolerance" in result

    def test_limited_tolerance(self):
        result = _interpret_tolerance(3.5)
        assert "Limited social tolerance" in result

    def test_low_tolerance(self):
        result = _interpret_tolerance(2.0)
        assert "Low social tolerance" in result

    def test_none_returns_none(self):
        assert _interpret_tolerance(None) is None


class TestInterpretGender:
    def test_strongly_egalitarian(self):
        result = _interpret_gender(2.5, 3.5, 3.5)
        assert "Strongly egalitarian" in result

    def test_traditional_preferences(self):
        result = _interpret_gender(1.2, 1.5, 1.5)
        assert "Traditional gender role" in result

    def test_all_none_returns_none(self):
        assert _interpret_gender(None, None, None) is None


class TestInterpretCivic:
    def test_active_participation(self):
        result = _interpret_civic(1.3, 1.4, 1.3)
        assert "frequent petition-signing" in result
        assert "frequent boycott participation" in result

    def test_limited_participation(self):
        result = _interpret_civic(2.5, 2.8, 2.7)
        assert "Limited engagement" in result

    def test_all_none_returns_none(self):
        assert _interpret_civic(None, None, None) is None


class TestInterpretLifeSatisfaction:
    def test_high_satisfaction(self):
        result = _interpret_life_satisfaction(8.0)
        assert "High life satisfaction" in result

    def test_moderate_satisfaction(self):
        result = _interpret_life_satisfaction(6.5)
        assert "Moderate life satisfaction" in result

    def test_lower_satisfaction(self):
        result = _interpret_life_satisfaction(4.5)
        assert "Lower life satisfaction" in result

    def test_none_returns_none(self):
        assert _interpret_life_satisfaction(None) is None


# ---------------------------------------------------------------------------
# Profile to insights tests
# ---------------------------------------------------------------------------


class TestProfileToInsights:
    def _make_profile(self, **dimension_overrides) -> WVSCountryProfile:
        """Create a test profile with optional dimension overrides."""
        dimensions = {col: None for col in ALL_DIMENSION_COLS}
        dimensions.update(dimension_overrides)
        return WVSCountryProfile(
            country_name="Test Country",
            iso_alpha2="TC",
            wave=6,
            dimensions=dimensions,
        )

    def test_full_profile_generates_three_sections(self):
        profile = self._make_profile(
            TRADRAT5=1.0,
            survself=1.0,
            A006=2.0,
            F063=7.0,
            A165=1.5,
            F118=6.0,
            E025=1.5,
            E026=2.0,
            E027=2.0,
            A170=7.0,
            C001=2.0,
            D059=3.0,
            D060=3.0,
        )
        sections = profile_to_insights(profile)
        assert len(sections) == 3

    def test_all_headings_start_with_prefix(self):
        profile = self._make_profile(
            TRADRAT5=1.0,
            survself=1.0,
            A165=1.5,
            D059=3.0,
            D060=3.0,
        )
        sections = profile_to_insights(profile)
        for section in sections:
            assert section["heading"].startswith(WVS_HEADING_PREFIX)

    def test_section_headings(self):
        profile = self._make_profile(
            TRADRAT5=1.0,
            survself=1.0,
            A165=1.5,
            A170=7.0,
            D059=3.0,
            D060=3.0,
        )
        sections = profile_to_insights(profile)
        headings = [s["heading"] for s in sections]
        assert f"{WVS_HEADING_PREFIX}: Cultural Values Profile" in headings
        assert f"{WVS_HEADING_PREFIX}: Social Trust & Civic Engagement" in headings
        assert f"{WVS_HEADING_PREFIX}: Gender & Economic Values" in headings

    def test_wave_number_in_first_section(self):
        profile = self._make_profile(TRADRAT5=1.0)
        sections = profile_to_insights(profile)
        assert any("Wave 6" in p for p in sections[0]["points"])

    def test_empty_dimensions_returns_empty(self):
        profile = self._make_profile()
        sections = profile_to_insights(profile)
        assert sections == []

    def test_partial_data_omits_empty_sections(self):
        """If only cultural values data is present, other sections are omitted."""
        profile = self._make_profile(TRADRAT5=0.5)
        sections = profile_to_insights(profile)
        assert len(sections) == 1
        assert "Cultural Values Profile" in sections[0]["heading"]

    def test_insights_json_schema(self):
        """Each section must have 'heading' (str) and 'points' (list of str)."""
        profile = self._make_profile(
            TRADRAT5=1.0,
            survself=1.0,
            A165=1.5,
            D059=3.0,
            D060=3.0,
        )
        sections = profile_to_insights(profile)
        for section in sections:
            assert isinstance(section["heading"], str)
            assert isinstance(section["points"], list)
            for point in section["points"]:
                assert isinstance(point, str)
                assert len(point) > 0


# ---------------------------------------------------------------------------
# CSV parsing tests
# ---------------------------------------------------------------------------


class TestParseWVSCSV:
    def _make_csv(self, rows: list[dict]) -> str:
        """Create a temporary CSV from row dicts, return path."""
        df = pd.DataFrame(rows)
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w")
        df.to_csv(tmp, index=False)
        tmp.close()
        return tmp.name

    def test_basic_parsing(self):
        csv_path = self._make_csv([
            {"Country": "United States", "Wave": 6, "TRADRAT5": 0.86, "survself": 1.10},
            {"Country": "Japan", "Wave": 6, "TRADRAT5": 1.27, "survself": 0.83},
        ])
        profiles = parse_wvs_csv(csv_path)
        assert len(profiles) == 2
        us = next(p for p in profiles if p.iso_alpha2 == "US")
        assert us.wave == 6
        assert us.dimensions["TRADRAT5"] == pytest.approx(0.86)

    def test_selects_most_recent_wave(self):
        csv_path = self._make_csv([
            {"Country": "Japan", "Wave": 3, "TRADRAT5": 0.5},
            {"Country": "Japan", "Wave": 6, "TRADRAT5": 1.27},
            {"Country": "Japan", "Wave": 4, "TRADRAT5": 0.8},
        ])
        profiles = parse_wvs_csv(csv_path)
        assert len(profiles) == 1
        assert profiles[0].wave == 6
        assert profiles[0].dimensions["TRADRAT5"] == pytest.approx(1.27)

    def test_unmapped_country_skipped(self):
        csv_path = self._make_csv([
            {"Country": "Atlantis", "Wave": 1, "TRADRAT5": 0.5},
            {"Country": "United States", "Wave": 6, "TRADRAT5": 0.86},
        ])
        profiles = parse_wvs_csv(csv_path)
        assert len(profiles) == 1
        assert profiles[0].iso_alpha2 == "US"

    def test_missing_dimension_is_none(self):
        csv_path = self._make_csv([
            {"Country": "Japan", "Wave": 6, "TRADRAT5": 1.27},
        ])
        profiles = parse_wvs_csv(csv_path)
        # survself not in CSV, should be None
        assert profiles[0].dimensions.get("survself") is None

    def test_nan_dimension_is_none(self):
        csv_path = self._make_csv([
            {"Country": "Japan", "Wave": 6, "TRADRAT5": float("nan")},
        ])
        profiles = parse_wvs_csv(csv_path)
        assert profiles[0].dimensions["TRADRAT5"] is None

    def test_iso_code_assignment(self):
        csv_path = self._make_csv([
            {"Country": "Great Britain", "Wave": 6, "TRADRAT5": 0.5},
            {"Country": "Czech Rep.", "Wave": 6, "TRADRAT5": 1.0},
        ])
        profiles = parse_wvs_csv(csv_path)
        codes = {p.iso_alpha2 for p in profiles}
        assert "GB" in codes
        assert "CZ" in codes

    def test_raw_data_includes_all_columns(self):
        """raw_data should contain all data columns from the CSV."""
        csv_path = self._make_csv([
            {
                "Country": "Japan",
                "Wave": 6,
                "TRADRAT5": 1.27,
                "survself": 0.83,
                "A001": 1.05,
                "V33": 2.5,
                "X999": 0.42,
            },
        ])
        profiles = parse_wvs_csv(csv_path)
        raw = profiles[0].raw_data
        # All data columns present (not Country/Wave)
        assert "TRADRAT5" in raw
        assert "A001" in raw
        assert "V33" in raw
        assert "X999" in raw
        assert "Country" not in raw
        assert "Wave" not in raw
        assert raw["A001"] == pytest.approx(1.05)

    def test_raw_data_nan_is_none(self):
        csv_path = self._make_csv([
            {"Country": "Japan", "Wave": 6, "A001": float("nan"), "A002": 1.5},
        ])
        profiles = parse_wvs_csv(csv_path)
        assert profiles[0].raw_data["A001"] is None
        assert profiles[0].raw_data["A002"] == pytest.approx(1.5)
