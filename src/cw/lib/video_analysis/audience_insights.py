"""
Audience insights generation using LLM.

Analyzes video content to generate audience targeting recommendations.
"""

import json
import logging
from typing import Dict

from cw.lib.prompts import render_prompt

logger = logging.getLogger(__name__)


def generate_audience_insights(
    script: Dict,
    visual_style: Dict,
    sentiment: Dict,
    transcription: Dict,
    categories: Dict,
    model_id: str = "Qwen/Qwen2.5-3B-Instruct",
    load_in_4bit: bool = False,
) -> Dict:
    """
    Generate audience targeting insights using LLM analysis.

    Args:
        script: Generated script data with scenes
        visual_style: Visual style analysis results
        sentiment: Sentiment analysis results
        transcription: Audio transcription data
        categories: Scene categorization summary
        model_id: LLM model to use for generation
        load_in_4bit: Whether to use 4-bit quantization

    Returns:
        Audience insights dictionary matching AudienceInsights schema

    Raises:
        Exception: If LLM generation fails (falls back to rule-based)
    """
    # Prepare context data for insights generation
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

    try:
        from cw.lib.pipeline.model_loader import get_model_loader
        from cw.lib.video_analysis.schemas import AudienceInsights

        logger.info(
            "Generating audience insights with LLM",
            extra={
                "model_id": model_id,
                "load_in_4bit": load_in_4bit,
            },
        )

        # Get model loader and generator
        loader = get_model_loader(model_id=model_id, load_in_4bit=load_in_4bit)
        generator = loader.get_generator(output_schema=AudienceInsights)

        # Render prompt template
        user_prompt = render_prompt("audience-insights", **context)

        # Apply chat template
        system_message = (
            "You are an expert marketing analyst specializing in audience "
            "segmentation and targeting. Produce ONLY valid JSON matching "
            "the requested schema — no commentary."
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ]
        prompt = loader.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # Generate insights with structured output
        logger.info("Invoking LLM for structured audience insights generation")
        raw_output = generator(prompt, max_new_tokens=4096)

        # Validate and parse output
        result = AudienceInsights.model_validate(
            json.loads(raw_output) if isinstance(raw_output, str) else raw_output
        )

        # Convert to dict format
        insights = result.model_dump()

        logger.info(
            "Audience insights generation complete",
            extra={
                "primary_audience_age": insights["primary_audience"]["demographics"][
                    "age_range"
                ],
                "secondary_audiences_count": len(insights["secondary_audiences"]),
                "high_fit_markets_count": len(
                    insights["market_potential"]["high_fit_markets"]
                ),
            },
        )

        return insights

    except Exception as e:
        logger.warning(
            f"LLM-based audience insights failed: {e}. Falling back to rule-based approach.",
            exc_info=True,
        )
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

    if "people" in primary_categories and "family" in str(
        context.get("script_scenes", [])
    ).lower():
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
        "reasoning": "Generated using rule-based heuristics from video analysis (LLM unavailable)",
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
                f"Content language is {language}",
                f"Primary sentiment is {sentiment}",
                "Consider cultural adaptation for non-primary markets",
            ],
        },
        "messaging_recommendations": messaging,
    }
