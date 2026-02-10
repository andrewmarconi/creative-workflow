"""Unit tests for audience insights schema validation."""

import pytest
from pydantic import ValidationError


def test_audience_insights_schema_valid():
    """Test that the schema validates expected output structure."""
    from cw.lib.video_analysis.schemas import AudienceInsights

    data = {
        "reasoning": "The video features family moments and positive sentiment, indicating a family-oriented target audience...",
        "primary_audience": {
            "demographics": {
                "age_range": "25-45",
                "gender": "all",
                "income_level": "middle to upper-middle",
            },
            "psychographics": {
                "values": ["family", "quality", "convenience"],
                "interests": ["cooking", "home life"],
                "lifestyle": "family-oriented",
            },
        },
        "secondary_audiences": [
            {
                "segment": "Young professionals",
                "fit_score": 0.75,
                "reasoning": "Convenience messaging resonates with busy lifestyle",
            }
        ],
        "market_potential": {
            "high_fit_markets": ["US", "UK", "DE"],
            "adaptation_needed": ["JP", "KR"],
            "considerations": ["Family messaging works well in Western markets"],
        },
        "messaging_recommendations": [
            "Emphasize family togetherness",
            "Highlight convenience",
        ],
    }

    # Should validate without errors
    result = AudienceInsights.model_validate(data)
    assert result.primary_audience.demographics.age_range == "25-45"
    assert "family" in result.primary_audience.psychographics.values
    assert len(result.secondary_audiences) == 1
    assert result.secondary_audiences[0].fit_score == 0.75


def test_audience_insights_schema_requires_reasoning():
    """Test that reasoning field is required."""
    from cw.lib.video_analysis.schemas import AudienceInsights

    data = {
        # Missing "reasoning" field
        "primary_audience": {
            "demographics": {
                "age_range": "25-45",
                "gender": "all",
                "income_level": "middle",
            },
            "psychographics": {
                "values": ["quality"],
                "interests": ["general"],
                "lifestyle": "varied",
            },
        },
        "secondary_audiences": [],
        "market_potential": {
            "high_fit_markets": ["US"],
            "considerations": ["Test"],
        },
        "messaging_recommendations": ["Test message"],
    }

    with pytest.raises(ValidationError) as exc_info:
        AudienceInsights.model_validate(data)

    # Check that the error mentions the missing field
    assert "reasoning" in str(exc_info.value)


def test_audience_insights_schema_validates_fit_score():
    """Test that fit_score is validated to be between 0.0 and 1.0."""
    from cw.lib.video_analysis.schemas import AudienceInsights

    data = {
        "reasoning": "Test reasoning",
        "primary_audience": {
            "demographics": {
                "age_range": "25-45",
                "gender": "all",
                "income_level": "middle",
            },
            "psychographics": {
                "values": ["quality"],
                "interests": ["general"],
                "lifestyle": "varied",
            },
        },
        "secondary_audiences": [
            {
                "segment": "Test segment",
                "fit_score": 1.5,  # Invalid - should be <= 1.0
                "reasoning": "Test",
            }
        ],
        "market_potential": {
            "high_fit_markets": ["US"],
            "considerations": ["Test"],
        },
        "messaging_recommendations": ["Test"],
    }

    with pytest.raises(ValidationError) as exc_info:
        AudienceInsights.model_validate(data)

    # Check that the error mentions the fit_score validation
    assert "fit_score" in str(exc_info.value)


def test_audience_insights_schema_defaults():
    """Test that optional fields have sensible defaults."""
    from cw.lib.video_analysis.schemas import AudienceInsights

    # Minimal valid data
    data = {
        "reasoning": "Test reasoning",
        "primary_audience": {
            "demographics": {
                "age_range": "all",
                "gender": "all",
                "income_level": "all",
            },
            "psychographics": {
                "values": ["quality"],
                "interests": ["general"],
                "lifestyle": "varied",
            },
        },
        "market_potential": {
            "high_fit_markets": ["US"],
            "considerations": ["Test"],
        },
        "messaging_recommendations": ["Test"],
        # Omit secondary_audiences and adaptation_needed - should use defaults
    }

    result = AudienceInsights.model_validate(data)
    assert result.secondary_audiences == []
    assert result.market_potential.adaptation_needed == []


def test_fallback_insights_structure():
    """Test that fallback insights match the schema."""
    from cw.lib.video_analysis.audience_insights import _generate_fallback_insights
    from cw.lib.video_analysis.schemas import AudienceInsights

    context = {
        "script_scenes": [],
        "dominant_colors": [],
        "avg_brightness": 0.5,
        "lighting_distribution": {},
        "overall_sentiment": "positive",
        "sentiment_score": 0.7,
        "transcription_language": "en",
        "primary_categories": ["people", "lifestyle"],
        "category_counts": {"people": 3, "lifestyle": 2},
    }

    insights = _generate_fallback_insights(context)

    # Should validate against the schema
    result = AudienceInsights.model_validate(insights)
    assert result.reasoning  # Should have reasoning field
    assert result.primary_audience.demographics.age_range
    assert len(result.market_potential.high_fit_markets) > 0
