"""Insights composition for multi-level adaptation guidance.

Aggregates insights from region → country → language → market into a single
hierarchical guidance document for LLM-based adaptations.
"""

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from cw.core.models import Country, Region


def compose_insights(adaptation_job) -> List[Dict[str, str]]:
    """Aggregate insights from region → country → language → market.

    Args:
        adaptation_job: AdaptationJob instance with dimensional references

    Returns:
        List of insight sections with source attribution:
        [
            {
                'source': 'Region: North America',
                'markdown': '### Cultural values\\n- ...'
            },
            ...
        ]
    """
    insights = []

    # 1. Region-level insights (if applicable)
    region = _get_region(adaptation_job)
    if region and region.insights:
        insights.append({"source": f"Region: {region.name}", "markdown": region.insights_as_markdown()})

    # 2. Country-level insights (if applicable)
    country = _get_country(adaptation_job)
    if country and country.insights:
        insights.append({"source": f"Country: {country.name}", "markdown": country.insights_as_markdown()})

    # 3. Language-level insights (always present)
    language = adaptation_job.effective_language
    if language and language.insights:
        insights.append({"source": f"Language: {language.name}", "markdown": language.insights_as_markdown()})

    # 4. Market-level insights (campaign-specific, for backward compatibility)
    if hasattr(adaptation_job, 'target_market') and adaptation_job.target_market:
        market = adaptation_job.target_market
        if market.rules:  # Note: 'rules' is legacy name, contains same structure as insights
            insights.append({"source": f"Market: {market.name}", "markdown": market.rules_as_markdown()})

    return insights


def compose_insights_as_markdown(adaptation_job) -> str:
    """Compose all insights into a single Markdown document.

    Args:
        adaptation_job: AdaptationJob instance

    Returns:
        Markdown string with all insights hierarchically organized
    """
    sections = compose_insights(adaptation_job)

    if not sections:
        return ""

    # Build target name from region/country/language
    target_parts = []
    if hasattr(adaptation_job, 'region') and adaptation_job.region:
        target_parts.append(adaptation_job.region.name)
    if hasattr(adaptation_job, 'country') and adaptation_job.country:
        target_parts.append(adaptation_job.country.name)
    if hasattr(adaptation_job, 'language') and adaptation_job.language:
        target_parts.append(f"({adaptation_job.language.code})")
    elif hasattr(adaptation_job, 'effective_language') and adaptation_job.effective_language:
        target_parts.append(f"({adaptation_job.effective_language.code})")

    target_name = " / ".join(target_parts) if target_parts else "Target Market"

    # Build full document
    lines = [f"# Adaptation Guidance for {target_name}", ""]

    for section in sections:
        lines.append(f"## {section['source']}")
        lines.append(section["markdown"])
        lines.append("")  # Blank line between sections

    return "\n".join(lines)


def _get_region(adaptation_job) -> Optional["Region"]:
    """Extract region from adaptation job (via market or direct reference).

    Priority:
    1. Direct region reference (if TVSpotAdaptation model exists)
    2. Market's regions (if AdaptationMarket has M2M to regions)
    3. Country's regions (via market's countries)

    Returns:
        Region instance or None
    """
    # Direct reference (TVSpotAdaptation model - Phase 5)
    if hasattr(adaptation_job, "region") and adaptation_job.region:
        return adaptation_job.region

    # Via market regions (M2M) - backward compatibility
    if hasattr(adaptation_job, 'target_market') and adaptation_job.target_market:
        market = adaptation_job.target_market
        if hasattr(market, "regions"):
            return market.regions.first()  # Pick first if multiple

    # Via country
    country = _get_country(adaptation_job)
    if country and hasattr(country, "regions"):
        return country.regions.first()

    return None


def _get_country(adaptation_job) -> Optional["Country"]:
    """Extract country from adaptation job.

    Priority:
    1. Direct country reference (if TVSpotAdaptation model exists)
    2. Market's countries (if AdaptationMarket has M2M)
    3. Language's countries (via effective_language)

    Returns:
        Country instance or None
    """
    # Direct reference (TVSpotAdaptation model - Phase 5)
    if hasattr(adaptation_job, "country") and adaptation_job.country:
        return adaptation_job.country

    # Via market countries (M2M) - backward compatibility
    if hasattr(adaptation_job, 'target_market') and adaptation_job.target_market:
        market = adaptation_job.target_market
        if hasattr(market, "countries"):
            return market.countries.first()

    # Via language
    language = adaptation_job.effective_language
    if language and hasattr(language, "countries"):
        # Prefer primary language countries
        return language.countries.filter(countrylanguage__is_primary=True).first()

    return None
