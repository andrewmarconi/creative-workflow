"""
Sentiment analysis for video content.

Analyzes sentiment from transcribed audio and visual data.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# Sentiment keywords for basic rule-based analysis
POSITIVE_KEYWORDS = {
    "happy", "joy", "love", "great", "excellent", "amazing", "wonderful",
    "best", "beautiful", "smile", "laugh", "excited", "fun", "delicious",
    "perfect", "fantastic", "awesome", "brilliant", "celebrate", "success",
    "win", "winner", "achieve", "dream", "new", "fresh", "clean", "bright",
    "better", "improve", "upgrade", "premium", "quality", "luxurious",
}

NEGATIVE_KEYWORDS = {
    "sad", "bad", "terrible", "awful", "hate", "angry", "problem", "issue",
    "difficult", "hard", "pain", "hurt", "wrong", "failed", "loss", "lose",
    "worry", "fear", "scared", "danger", "risk", "old", "dirty", "broken",
    "sick", "tired", "stress", "boring", "dull", "cheap", "poor",
}

NEUTRAL_KEYWORDS = {
    "maybe", "perhaps", "possibly", "consider", "option", "choice",
    "compare", "different", "alternative", "available", "now", "here",
    "today", "simple", "easy", "quick", "find", "discover", "learn",
}


def analyze_text_sentiment(text: str) -> Dict:
    """
    Analyze sentiment from text using keyword-based approach.

    Args:
        text: Text to analyze (e.g., transcription)

    Returns:
        Sentiment analysis:
        {
            "sentiment": "positive",  # positive | negative | neutral
            "score": 0.75,  # -1.0 (very negative) to 1.0 (very positive)
            "confidence": 0.68,  # 0-1 confidence in classification
        }
    """
    if not text:
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.0,
        }

    # Normalize text
    text_lower = text.lower()
    words = text_lower.split()

    # Count keyword matches
    positive_count = sum(1 for word in words if word in POSITIVE_KEYWORDS)
    negative_count = sum(1 for word in words if word in NEGATIVE_KEYWORDS)
    neutral_count = sum(1 for word in words if word in NEUTRAL_KEYWORDS)

    # Calculate total matches and score
    total_matches = positive_count + negative_count + neutral_count

    if total_matches == 0:
        # No keywords found = neutral with low confidence
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "confidence": 0.1,
        }

    # Calculate sentiment score (-1 to 1)
    # Positive keywords add, negative subtract, neutral doesn't affect
    raw_score = (positive_count - negative_count) / max(len(words), 1)
    score = max(-1.0, min(1.0, raw_score * 5))  # Scale and clamp

    # Determine sentiment category
    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    # Calculate confidence based on keyword density
    confidence = min(1.0, total_matches / max(len(words) / 10, 1))

    return {
        "sentiment": sentiment,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
    }


def analyze_visual_sentiment(visual_style: Dict, objects: Dict) -> Dict:
    """
    Analyze sentiment from visual characteristics.

    Args:
        visual_style: Visual style analysis from analyze_visual_style()
        objects: Object summary from summarize_objects()

    Returns:
        Visual sentiment:
        {
            "sentiment": "positive",
            "score": 0.6,
            "brightness_factor": 0.7,  # Higher brightness = more positive
            "object_factor": 0.5,  # People/happy objects = more positive
        }
    """
    # Brightness-based sentiment (brighter = more positive)
    brightness = visual_style.get("avg_brightness", 0.5)

    # Normalize brightness to sentiment score (-1 to 1)
    # 0.0-0.3: negative, 0.3-0.6: neutral, 0.6-1.0: positive
    brightness_factor = (brightness - 0.5) * 2  # Map to -1 to 1

    # Object-based sentiment
    # Presence of people often indicates positive/engaging content
    object_classes = objects.get("classes", {})
    has_people = "person" in object_classes
    person_count = object_classes.get("person", {}).get("count", 0)

    # Simple heuristic: people = slightly more positive
    object_factor = 0.2 if has_people else 0.0
    if person_count > 2:
        object_factor = 0.4  # Multiple people = more positive

    # Combine factors
    raw_score = (brightness_factor * 0.7) + (object_factor * 0.3)
    score = max(-1.0, min(1.0, raw_score))

    # Determine sentiment
    if score > 0.2:
        sentiment = "positive"
    elif score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "sentiment": sentiment,
        "score": round(score, 3),
        "brightness_factor": round(brightness_factor, 3),
        "object_factor": round(object_factor, 3),
    }


def analyze_sentiment(
    transcription: Dict,
    visual_style: Dict,
    objects_summary: Dict,
) -> Dict:
    """
    Comprehensive sentiment analysis combining audio and visual data.

    Args:
        transcription: Transcription data with segments
        visual_style: Visual style analysis results
        objects_summary: Object detection summary

    Returns:
        Combined sentiment analysis:
        {
            "overall_sentiment": "positive",
            "overall_score": 0.65,  # -1.0 to 1.0
            "confidence": 0.72,
            "text_sentiment": {...},
            "visual_sentiment": {...},
        }
    """
    logger.info("Analyzing sentiment from audio and visual data")

    # Analyze text sentiment from transcription
    full_text = " ".join(
        segment.get("text", "")
        for segment in transcription.get("segments", [])
    )
    text_sentiment = analyze_text_sentiment(full_text)

    # Analyze visual sentiment
    visual_sentiment = analyze_visual_sentiment(visual_style, objects_summary)

    # Combine text and visual sentiment
    # Weight: 60% text (what's said), 40% visual (how it looks)
    text_weight = 0.6
    visual_weight = 0.4

    combined_score = (
        text_sentiment["score"] * text_weight +
        visual_sentiment["score"] * visual_weight
    )

    # Determine overall sentiment
    if combined_score > 0.2:
        overall_sentiment = "positive"
    elif combined_score < -0.2:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"

    # Average confidences
    avg_confidence = (
        text_sentiment.get("confidence", 0.5) * text_weight +
        0.6 * visual_weight  # Visual is less confident (simpler analysis)
    )

    result = {
        "overall_sentiment": overall_sentiment,
        "overall_score": round(combined_score, 3),
        "confidence": round(avg_confidence, 3),
        "text_sentiment": text_sentiment,
        "visual_sentiment": visual_sentiment,
    }

    logger.info(f"Sentiment analysis complete: {overall_sentiment} (score: {combined_score:.2f})")
    return result
