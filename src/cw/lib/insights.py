"""Insights composition for multi-level adaptation guidance.

Aggregates insights from region → country → language into a single
hierarchical guidance document for LLM-based adaptations.
"""

from typing import Dict, List


def compose_insights(video_ad_unit) -> List[Dict[str, str]]:
    """Aggregate insights from region, country, language, and persona segments.

    Args:
        video_ad_unit: VideoAdUnit instance with dimensional references
            (region, country, language, persona)

    Returns:
        List of dicts, each with ``'source'`` (e.g. ``'Region: North America'``)
        and ``'markdown'`` (rendered insight content) keys.
    """
    insights = []

    # 1. Region-level insights (if applicable)
    if video_ad_unit.region and video_ad_unit.region.insights:
        insights.append({
            "source": f"Region: {video_ad_unit.region.name}",
            "markdown": video_ad_unit.region.insights_as_markdown()
        })

    # 2. Country-level insights (if applicable)
    if video_ad_unit.country and video_ad_unit.country.insights:
        insights.append({
            "source": f"Country: {video_ad_unit.country.name}",
            "markdown": video_ad_unit.country.insights_as_markdown()
        })

    # 3. Language-level insights (always present)
    if video_ad_unit.language and video_ad_unit.language.insights:
        insights.append({
            "source": f"Language: {video_ad_unit.language.name}",
            "markdown": video_ad_unit.language.insights_as_markdown()
        })

    # 4. Persona segment insights (if persona is set)
    if video_ad_unit.persona:
        # Get all segments attached to the persona, ordered by category
        segments = video_ad_unit.persona.segments.filter(is_active=True).order_by(
            "personasegment__order_index", "category", "vector"
        )

        for segment in segments:
            if segment.insights:
                source = f"{segment.get_category_display()}: {segment.vector} → {segment.value}"
                insights.append({
                    "source": source,
                    "markdown": segment.insights_as_markdown()
                })

    return insights


def compose_insights_as_markdown(video_ad_unit) -> str:
    """Compose all insights into a single Markdown document.

    Args:
        video_ad_unit: VideoAdUnit instance

    Returns:
        Markdown string with all insights hierarchically organized
    """
    sections = compose_insights(video_ad_unit)

    if not sections:
        return ""

    # Build target name from persona or region/country/language
    if video_ad_unit.persona:
        target_name = video_ad_unit.persona.name
        # Add geographic context if present
        geo_parts = []
        if video_ad_unit.region:
            geo_parts.append(video_ad_unit.region.name)
        if video_ad_unit.country:
            geo_parts.append(video_ad_unit.country.name)
        if video_ad_unit.language:
            geo_parts.append(f"({video_ad_unit.language.code})")
        if geo_parts:
            target_name = f"{target_name} — {' / '.join(geo_parts)}"
    else:
        # Fallback to geographic-only naming
        target_parts = []
        if video_ad_unit.region:
            target_parts.append(video_ad_unit.region.name)
        if video_ad_unit.country:
            target_parts.append(video_ad_unit.country.name)
        if video_ad_unit.language:
            target_parts.append(f"({video_ad_unit.language.code})")
        target_name = " / ".join(target_parts) if target_parts else "Target Market"

    # Build full document
    lines = [f"# Adaptation Guidance for {target_name}", ""]

    for section in sections:
        lines.append(f"## {section['source']}")
        lines.append(section["markdown"])
        lines.append("")  # Blank line between sections

    return "\n".join(lines)
