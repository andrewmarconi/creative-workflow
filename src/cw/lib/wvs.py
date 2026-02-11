"""World Values Survey (WVS) data parser.

Downloads, parses, and transforms WVS country-level aggregated data
into structured insights for enriching Country model records.

Data source: https://www.kaggle.com/datasets/fernandol/world-values-survey
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

_CODEBOOK_PATH = Path(__file__).resolve().parents[3] / "data" / "wvs_codebook.json"
_codebook_cache: dict[str, dict] | None = None


# ---------------------------------------------------------------------------
# WVS country name → ISO 3166-1 alpha-2 mapping
# The Kaggle dataset uses English country names, not ISO codes.
# ---------------------------------------------------------------------------
WVS_COUNTRY_TO_ISO: dict[str, str] = {
    "Albania": "AL",
    "Algeria": "DZ",
    "Andorra": "AD",
    "Argentina": "AR",
    "Armenia": "AM",
    "Australia": "AU",
    "Azerbaijan": "AZ",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Belarus": "BY",
    "Bosnia": "BA",
    "Bosnian Federation": "BA",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Burkina Faso": "BF",
    "Canada": "CA",
    "Chile": "CL",
    "China": "CN",
    "Colombia": "CO",
    "Croatia": "HR",
    "Cyprus (G)": "CY",
    "Czech Rep.": "CZ",
    "Dominican Rep.": "DO",
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "Estonia": "EE",
    "Ethiopia": "ET",
    "Finland": "FI",
    "France": "FR",
    "Georgia": "GE",
    "Germany": "DE",
    "Ghana": "GH",
    "Great Britain": "GB",
    "Guatemala": "GT",
    "Hong Kong": "HK",
    "Hungary": "HU",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Iraq": "IQ",
    "Israel": "IL",
    "Italy": "IT",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Libya": "LY",
    "Lithuania": "LT",
    "Macedonia": "MK",
    "Malaysia": "MY",
    "Mali": "ML",
    "Mexico": "MX",
    "Moldova": "MD",
    "Morocco": "MA",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Nigeria": "NG",
    "Norway": "NO",
    "Pakistan": "PK",
    "Palestine": "PS",
    "Peru": "PE",
    "Philippines": "PH",
    "Poland": "PL",
    "Puerto Rico": "PR",
    "Qatar": "QA",
    "Romania": "RO",
    "Russia": "RU",
    "Rwanda": "RW",
    "Saudi Arabia": "SA",
    "Serbia and Montenegro": "RS",
    "Singapore": "SG",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Taiwan": "TW",
    "Tanzania": "TZ",
    "Thailand": "TH",
    "Trinidad and Tobago": "TT",
    "Tunisia": "TN",
    "Turkey": "TR",
    "Uganda": "UG",
    "Ukraine": "UA",
    "United States": "US",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
    "Venezuela": "VE",
    "Viet Nam": "VN",
    "Yemen": "YE",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
}

# ---------------------------------------------------------------------------
# WVS variables used for cultural dimension extraction
# ---------------------------------------------------------------------------

# Pre-computed Inglehart-Welzel cultural map indices
COL_TRAD_SECULAR = "TRADRAT5"  # Traditional vs. Secular-Rational
COL_SURV_SELFEXP = "survself"  # Survival vs. Self-Expression

# Individual variables
COL_TRUST = "A165"  # Most people can be trusted (1=trust, 2=careful)
COL_LIFE_SAT = "A170"  # Life satisfaction (1=dissatisfied .. 10=satisfied)
COL_RELIGION_IMP = "A006"  # Importance of religion (1=very .. 4=not at all)
COL_GOD_IMP = "F063"  # Importance of God (1=not at all .. 10=very)
COL_HOMOSEX_OK = "F118"  # Justifiable: homosexuality (1=never .. 10=always)
COL_MEN_JOBS = "C001"  # Men should have more right to job (1=agree, 2=disagree, 3=neither)
COL_MEN_LEADERS = "D059"  # Men better political leaders (1=agree strongly .. 4=strongly disagree)
COL_UNI_BOYS = "D060"  # Uni more important for boys (1=agree strongly .. 4=strongly disagree)
COL_PETITION = "E025"  # Signed petition (1=have done, 2=might do, 3=never)
COL_BOYCOTT = "E026"  # Joined boycott (1=have done, 2=might do, 3=never)
COL_DEMO = "E027"  # Attended demonstration (1=have done, 2=might do, 3=never)

ALL_DIMENSION_COLS = [
    COL_TRAD_SECULAR,
    COL_SURV_SELFEXP,
    COL_TRUST,
    COL_LIFE_SAT,
    COL_RELIGION_IMP,
    COL_GOD_IMP,
    COL_HOMOSEX_OK,
    COL_MEN_JOBS,
    COL_MEN_LEADERS,
    COL_UNI_BOYS,
    COL_PETITION,
    COL_BOYCOTT,
    COL_DEMO,
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class WVSCountryProfile:
    """Aggregated WVS cultural profile for a single country."""

    country_name: str
    iso_alpha2: str
    wave: int
    dimensions: dict[str, float | None] = field(default_factory=dict)
    raw_data: dict[str, float | None] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------


def parse_wvs_csv(csv_path: str) -> list[WVSCountryProfile]:
    """Parse WVS per-country CSV and return profiles for the most recent wave.

    Args:
        csv_path: Path to the WVS_per_Country.csv file.

    Returns:
        List of WVSCountryProfile, one per country (most recent wave only).
        Countries without an ISO mapping are silently skipped.
        Each profile includes both the curated ``dimensions`` dict (for
        default insight generation) and the full ``raw_data`` dict (all
        ~945 variable means for dynamic theme-based lookups).
    """
    df = pd.read_csv(csv_path)

    # Keep only the most recent wave per country
    idx = df.groupby("Country")["Wave"].idxmax()
    latest = df.loc[idx]

    # Identify data columns (everything except Country and Wave)
    data_cols = [c for c in df.columns if c not in ("Country", "Wave")]

    profiles: list[WVSCountryProfile] = []
    for _, row in latest.iterrows():
        country_name = row["Country"]
        iso_code = WVS_COUNTRY_TO_ISO.get(country_name)
        if iso_code is None:
            continue

        # Extract curated dimension subset (for default insights)
        dimensions: dict[str, float | None] = {}
        for col in ALL_DIMENSION_COLS:
            if col in row.index:
                val = row[col]
                dimensions[col] = float(val) if pd.notna(val) else None
            else:
                dimensions[col] = None

        # Extract all raw data (for dynamic theme-based lookups)
        # Skip non-numeric columns (e.g. S009/S009A contain country codes)
        raw_data: dict[str, float | None] = {}
        for col in data_cols:
            val = row[col]
            if pd.isna(val):
                raw_data[col] = None
            elif isinstance(val, (int, float)):
                raw_data[col] = float(val)
            else:
                try:
                    raw_data[col] = float(val)
                except (ValueError, TypeError):
                    pass

        profiles.append(
            WVSCountryProfile(
                country_name=country_name,
                iso_alpha2=iso_code,
                wave=int(row["Wave"]),
                dimensions=dimensions,
                raw_data=raw_data,
            )
        )

    return profiles


# ---------------------------------------------------------------------------
# Score interpretation helpers
# ---------------------------------------------------------------------------


def _interpret_trad_secular(score: float | None) -> str | None:
    """Interpret Traditional/Secular-Rational index.

    Higher values = more secular-rational.
    Typical range: roughly -2.0 to +2.0.
    """
    if score is None:
        return None
    if score > 1.0:
        return f"Strongly secular-rational (index: {score:.2f}). Society places less emphasis on religion, deference to authority, and traditional family values. Greater acceptance of divorce, abortion, and individual autonomy."
    if score > 0.5:
        return f"Moderately secular-rational (index: {score:.2f}). Societal attitudes lean toward secular governance and rational-legal authority, though traditional values retain some influence."
    if score > -0.5:
        return f"Mixed traditional and secular values (index: {score:.2f}). Society balances religious/traditional values with secular modernization. Both orientations coexist."
    return f"Strongly traditional (index: {score:.2f}). Society emphasizes religion, national pride, authority, and traditional family structures. Conformity and respect for elders are highly valued."


def _interpret_surv_selfexp(score: float | None) -> str | None:
    """Interpret Survival/Self-Expression index.

    Higher values = more self-expression oriented.
    Typical range: roughly -2.0 to +2.0.
    """
    if score is None:
        return None
    if score > 1.0:
        return f"Strong self-expression values (index: {score:.2f}). High priority on individual freedom, quality of life, environmental protection, tolerance of diversity, and civic participation."
    if score > 0.5:
        return f"Moderate self-expression values (index: {score:.2f}). Growing emphasis on quality of life, tolerance, and personal autonomy alongside residual concerns about economic and physical security."
    if score > -0.5:
        return f"Transitional between survival and self-expression (index: {score:.2f}). Economic security remains important but post-materialist values are emerging."
    return f"Strong survival values (index: {score:.2f}). High priority on economic and physical security, with lower tolerance for outgroups and limited emphasis on self-expression or civic engagement."


def _interpret_trust(score: float | None) -> str | None:
    """Interpret generalized social trust (A165).

    Scale: 1 = Most people can be trusted, 2 = Can't be too careful.
    Lower mean = higher trust society.
    """
    if score is None:
        return None
    trust_pct = round((2.0 - score) * 100)
    trust_pct = max(0, min(100, trust_pct))
    if trust_pct >= 60:
        return f"High social trust ({trust_pct}% say most people can be trusted). Strong foundation for cooperative messaging and community-oriented appeals."
    if trust_pct >= 40:
        return f"Moderate social trust ({trust_pct}% say most people can be trusted). Audiences may respond well to credibility signals and social proof."
    if trust_pct >= 20:
        return f"Low social trust ({trust_pct}% say most people can be trusted). Personal relationships and trusted intermediaries carry more weight than institutional endorsements."
    return f"Very low social trust ({trust_pct}% say most people can be trusted). Strong reliance on family, close networks, and personal experience over external claims."


def _interpret_religion(
    importance: float | None, god_importance: float | None
) -> str | None:
    """Interpret religious importance.

    A006: 1=very important .. 4=not at all.
    F063: 1=not at all important .. 10=very important.
    """
    parts = []
    if god_importance is not None:
        if god_importance >= 8.0:
            parts.append(f"God is very important in daily life (mean: {god_importance:.1f}/10)")
        elif god_importance >= 5.0:
            parts.append(f"God holds moderate importance (mean: {god_importance:.1f}/10)")
        else:
            parts.append(f"God is relatively unimportant in daily life (mean: {god_importance:.1f}/10)")

    if importance is not None:
        if importance <= 1.5:
            parts.append("religion is a core life priority")
        elif importance <= 2.5:
            parts.append("religion plays a significant role")
        elif importance <= 3.0:
            parts.append("religion has moderate relevance")
        else:
            parts.append("religion is peripheral to most people's lives")

    if not parts:
        return None
    return f"Religious significance: {'; '.join(parts)}. Consider the role of faith-based references and spiritual imagery in creative content."


def _interpret_gender(
    men_jobs: float | None,
    men_leaders: float | None,
    uni_boys: float | None,
) -> str | None:
    """Interpret gender equality attitudes.

    C001: Men should have more right to job (1=agree, 2=disagree, 3=neither).
    D059: Men better political leaders (1=agree strongly .. 4=disagree strongly).
    D060: Uni more important for boys (1=agree strongly .. 4=disagree strongly).
    """
    signals = []
    if men_leaders is not None:
        if men_leaders >= 3.0:
            signals.append("strong disagreement that men are better leaders")
        elif men_leaders >= 2.5:
            signals.append("moderate disagreement that men are better leaders")
        else:
            signals.append("some support for male leadership preference")

    if uni_boys is not None:
        if uni_boys >= 3.0:
            signals.append("strong support for equal educational access")
        elif uni_boys >= 2.5:
            signals.append("moderate support for equal education")
        else:
            signals.append("some preference for male education priority")

    if not signals:
        return None

    # Determine overall label
    egalitarian_score = 0
    count = 0
    if men_leaders is not None:
        egalitarian_score += (men_leaders - 1) / 3  # normalize to 0-1
        count += 1
    if uni_boys is not None:
        egalitarian_score += (uni_boys - 1) / 3
        count += 1
    if men_jobs is not None:
        # C001 is different: 2=disagree (egalitarian), 1=agree, 3=neither
        egalitarian_score += 1.0 if men_jobs >= 2.0 else 0.0
        count += 1

    avg = egalitarian_score / count if count else 0.5

    if avg >= 0.7:
        label = "Strongly egalitarian"
    elif avg >= 0.5:
        label = "Moderately egalitarian"
    elif avg >= 0.3:
        label = "Mixed gender attitudes"
    else:
        label = "Traditional gender role preferences"

    return f"{label}: {', '.join(signals)}. Gender portrayal in creative content should align with these societal expectations."


def _interpret_civic(
    petition: float | None,
    boycott: float | None,
    demo: float | None,
) -> str | None:
    """Interpret civic participation.

    E025/E026/E027: 1=have done, 2=might do, 3=would never do.
    Lower mean = more participatory.
    """
    activities = []
    if petition is not None:
        if petition <= 1.5:
            activities.append("frequent petition-signing")
        elif petition <= 2.0:
            activities.append("moderate petition engagement")
    if boycott is not None:
        if boycott <= 1.5:
            activities.append("frequent boycott participation")
        elif boycott <= 2.0:
            activities.append("some boycott willingness")
    if demo is not None:
        if demo <= 1.5:
            activities.append("active demonstration attendance")
        elif demo <= 2.0:
            activities.append("some demonstration openness")

    if not activities:
        if petition is not None or boycott is not None or demo is not None:
            return "Civic participation: Limited engagement with political actions such as petitions, boycotts, and demonstrations. Audiences may be less responsive to activism-oriented messaging."
        return None

    return f"Civic participation: {', '.join(activities)}. Audiences may be receptive to cause-driven and purpose-led brand messaging."


def _interpret_tolerance(homosex_ok: float | None) -> str | None:
    """Interpret social tolerance via homosexuality justifiability (F118).

    Scale: 1 = never justifiable .. 10 = always justifiable.
    """
    if homosex_ok is None:
        return None
    if homosex_ok >= 7.0:
        return f"High social tolerance (homosexuality acceptance: {homosex_ok:.1f}/10). Society is broadly open to diverse identities and lifestyles in media and advertising."
    if homosex_ok >= 5.0:
        return f"Moderate social tolerance (homosexuality acceptance: {homosex_ok:.1f}/10). Growing openness to diversity, though some segments remain conservative."
    if homosex_ok >= 3.0:
        return f"Limited social tolerance (homosexuality acceptance: {homosex_ok:.1f}/10). Diverse representation may require careful, culturally sensitive framing."
    return f"Low social tolerance (homosexuality acceptance: {homosex_ok:.1f}/10). LGBTQ+ themes in creative content carry significant risk and should be approached with extreme care."


def _interpret_life_satisfaction(score: float | None) -> str | None:
    """Interpret life satisfaction (A170). Scale: 1-10."""
    if score is None:
        return None
    if score >= 7.5:
        return f"High life satisfaction (mean: {score:.1f}/10). Audiences are generally optimistic; aspirational and positive messaging resonates."
    if score >= 6.0:
        return f"Moderate life satisfaction (mean: {score:.1f}/10). Mix of optimism and realism; practical benefit-driven messaging may be effective."
    return f"Lower life satisfaction (mean: {score:.1f}/10). Audiences may respond more to empathy-driven, improvement-oriented, or escapist narratives."


# ---------------------------------------------------------------------------
# Insight generation
# ---------------------------------------------------------------------------

WVS_HEADING_PREFIX = "WVS"


def profile_to_insights(profile: WVSCountryProfile) -> list[dict]:
    """Convert a WVS country profile into insights sections.

    Returns a list of dicts matching the insights JSON schema:
    ``[{"heading": "WVS: ...", "points": [...]}]``

    Sections with no available data are omitted entirely.
    """
    d = profile.dimensions
    sections: list[dict] = []

    # --- Section 1: Cultural Values Profile (Inglehart-Welzel axes) ---
    values_points = []

    trad = _interpret_trad_secular(d.get(COL_TRAD_SECULAR))
    if trad:
        values_points.append(f"Traditional/Secular-Rational axis: {trad}")

    surv = _interpret_surv_selfexp(d.get(COL_SURV_SELFEXP))
    if surv:
        values_points.append(f"Survival/Self-Expression axis: {surv}")

    religion = _interpret_religion(d.get(COL_RELIGION_IMP), d.get(COL_GOD_IMP))
    if religion:
        values_points.append(religion)

    if values_points:
        values_points.append(f"Data source: WVS Wave {profile.wave}")
        sections.append({
            "heading": f"{WVS_HEADING_PREFIX}: Cultural Values Profile",
            "points": values_points,
        })

    # --- Section 2: Social Trust & Civic Engagement ---
    social_points = []

    trust = _interpret_trust(d.get(COL_TRUST))
    if trust:
        social_points.append(trust)

    tolerance = _interpret_tolerance(d.get(COL_HOMOSEX_OK))
    if tolerance:
        social_points.append(tolerance)

    civic = _interpret_civic(
        d.get(COL_PETITION), d.get(COL_BOYCOTT), d.get(COL_DEMO)
    )
    if civic:
        social_points.append(civic)

    life_sat = _interpret_life_satisfaction(d.get(COL_LIFE_SAT))
    if life_sat:
        social_points.append(life_sat)

    if social_points:
        sections.append({
            "heading": f"{WVS_HEADING_PREFIX}: Social Trust & Civic Engagement",
            "points": social_points,
        })

    # --- Section 3: Gender & Economic Values ---
    gender_points = []

    gender = _interpret_gender(
        d.get(COL_MEN_JOBS), d.get(COL_MEN_LEADERS), d.get(COL_UNI_BOYS)
    )
    if gender:
        gender_points.append(gender)

    if gender_points:
        sections.append({
            "heading": f"{WVS_HEADING_PREFIX}: Gender & Economic Values",
            "points": gender_points,
        })

    return sections


# ---------------------------------------------------------------------------
# Codebook loader
# ---------------------------------------------------------------------------


def load_codebook() -> dict[str, dict]:
    """Load the WVS variable codebook from ``data/wvs_codebook.json``.

    Returns a dict mapping variable codes to ``{"label": str, "theme": str}``.
    The result is cached at module level after the first call.

    The codebook file is generated by ``manage.py import_wvs`` from the
    Kaggle dataset's ``Code_book.csv``.
    """
    global _codebook_cache
    if _codebook_cache is not None:
        return _codebook_cache

    if not _CODEBOOK_PATH.exists():
        _codebook_cache = {}
        return _codebook_cache

    with open(_CODEBOOK_PATH) as f:
        _codebook_cache = json.load(f)
    return _codebook_cache
