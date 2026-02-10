"""
Audience insights generation using LLM.

Analyzes video content to generate audience targeting recommendations.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def generate_audience_insights(
    script: Dict,
    visual_style: Dict,
    sentiment: Dict,
    transcription: Dict,
    categories: Dict,
) -> Dict:
    """
    Generate audience targeting insights using LLM analysis.

    Args:
        script: Generated script data with scenes
        visual_style: Visual style analysis results
        sentiment: Sentiment analysis results
        transcription: Audio transcription data
        categories: Scene categorization summary

    Returns:
        Audience insights dictionary:
        {
            "primary_audience": {
                "demographics": {
                    "age_range": "25-45",
                    "gender": "all",
                    "income_level": "middle to upper-middle"
                },
                "psychographics": {
                    "values": ["family", "quality", "convenience"],
                    "interests": ["cooking", "home life", "wellness"],
                    "lifestyle": "family-oriented, health-conscious"
                }
            },
            "secondary_audiences": [
                {
                    "segment": "Young professionals",
                    "fit_score": 0.75,
                    "reasoning": "..."
                }
            ],
            "market_potential": {
                "high_fit_markets": ["US", "UK", "DE", "AU"],
                "adaptation_needed": ["JP", "KR", "CN"],
                "considerations": [
                    "Family-focused messaging resonates in Western markets",
                    "May need cultural adaptation for Asian markets"
                ]
            },
            "messaging_recommendations": [
                "Emphasize family togetherness and quality time",
                "Highlight convenience and ease of use",
                "Use warm, inviting visual style"
            ]
        }

    Raises:
        Exception: If LLM generation fails
    """
    logger.info("Generating audience insights with LLM")

    try:
        from cw.lib.prompts import render_prompt
        from cw.lib.pipeline.state import PipelineModelLoader

        # Prepare context data for prompt
        context = {
            "script_scenes": script.get("scenes", []),
            "dominant_colors": visual_style.get("dominant_colors", []),
            "avg_brightness": visual_style.get("avg_brightness", 0),
            "lighting_distribution": visual_style.get("lighting_distribution", {}),
            "overall_sentiment": sentiment.get("overall_sentiment", "neutral"),
            "sentiment_score": sentiment.get("overall_score", 0),
            "transcription_language": transcription.get("language", "unknown"),
            "primary_categories": categories.get("primary_categories", []),
            "category_counts": categories.get("category_counts", {}),
        }

        # Render prompt template
        prompt = render_prompt("audience-insights", **context)

        # Get LLM generator for audience insights node
        loader = PipelineModelLoader()
        generator = loader.get_generator(
            state=None,
            schema=None,
            node_key="audience_insights",
        )

        # Generate insights
        logger.info("Invoking LLM for audience insights generation")
        response = generator.invoke(prompt)

        # Parse response
        insights = json.loads(response.content)

        logger.info("Audience insights generation complete")
        return insights

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Return fallback insights
        return _generate_fallback_insights(context)

    except Exception as e:
        logger.error(f"Audience insights generation failed: {e}", exc_info=True)
        # Return fallback insights
        return _generate_fallback_insights(context)


def _generate_fallback_insights(context: Dict) -> Dict:
    """
    Generate basic fallback insights when LLM is unavailable.

    Uses rule-based heuristics from video analysis data.
    """
    logger.info("Generating fallback audience insights (rule-based)")

    primary_categories = context.get("primary_categories", [])
    sentiment = context.get("overall_sentiment", "neutral")

    # Simple demographic inference from categories
    demographics = {"age_range": "all", "gender": "all", "income_level": "all"}

    if "people" in primary_categories and "family" in str(context.get("script_scenes", [])).lower():
        demographics["age_range"] = "25-54"
        demographics["income_level"] = "middle to upper-middle"

    if "technology" in primary_categories:
        demographics["age_range"] = "18-45"

    if "sports" in primary_categories:
        demographics["age_range"] = "18-34"

    # Simple psychographic inference
    values = []
    interests = []

    if "people" in primary_categories:
        values.append("relationships")
        interests.append("social activities")

    if "food" in primary_categories:
        values.append("quality")
        interests.append("cooking")

    if "lifestyle" in primary_categories:
        values.append("comfort")
        values.append("family")

    if "technology" in primary_categories:
        values.append("innovation")
        interests.append("technology")

    # Market potential based on language and categories
    language = context.get("transcription_language", "en")
    high_fit_markets = []

    if language == "en":
        high_fit_markets = ["US", "UK", "CA", "AU"]
    elif language == "es":
        high_fit_markets = ["ES", "MX", "AR"]
    elif language == "de":
        high_fit_markets = ["DE", "AT", "CH"]
    elif language == "fr":
        high_fit_markets = ["FR", "CA", "BE"]
    else:
        high_fit_markets = ["US"]  # Default

    # Messaging recommendations based on sentiment
    messaging = []
    if sentiment == "positive":
        messaging.append("Emphasize happiness and satisfaction")
        messaging.append("Use uplifting, energetic tone")
    elif sentiment == "negative":
        messaging.append("Address pain points and solutions")
        messaging.append("Focus on problem-solving benefits")
    else:
        messaging.append("Present clear, factual information")
        messaging.append("Balance emotional and rational appeals")

    return {
        "primary_audience": {
            "demographics": demographics,
            "psychographics": {
                "values": values if values else ["quality", "value"],
                "interests": interests if interests else ["general"],
                "lifestyle": "varied",
            },
        },
        "secondary_audiences": [],
        "market_potential": {
            "high_fit_markets": high_fit_markets,
            "adaptation_needed": [],
            "considerations": [
                "Fallback insights generated without LLM analysis",
                "Limited accuracy - consider manual review",
            ],
        },
        "messaging_recommendations": messaging if messaging else [
            "Tailor messaging to target audience",
            "Test different approaches",
        ],
        "generated_by": "fallback_rules",
    }
