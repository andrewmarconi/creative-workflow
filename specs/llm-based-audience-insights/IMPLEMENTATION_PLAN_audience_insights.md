# Implementation Plan: LLM-Based Audience Insights

## Overview
Implement structured LLM generation for audience insights using the same pattern as the adaptation pipeline (Pydantic schemas + Outlines + PipelineModelLoader).

## Current State
- ✅ Rule-based fallback working (good for MVP)
- ❌ LLM integration incomplete (was using wrong API)
- ❌ No Pydantic schema defined for audience insights output

## Implementation Steps

### Step 1: Define Pydantic Schema for Audience Insights

**File**: `src/cw/lib/video_analysis/schemas.py` (new file)

```python
"""Pydantic schemas for video analysis outputs."""

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    """Demographic profile for audience segment."""

    age_range: str = Field(
        description="Target age range (e.g., '25-45', '18-34')"
    )
    gender: str = Field(
        description="Gender targeting: 'male', 'female', 'all', or specific ratio"
    )
    income_level: str = Field(
        description="Income bracket: 'all', 'lower', 'middle', 'upper-middle', 'upper'"
    )


class Psychographics(BaseModel):
    """Psychographic profile for audience segment."""

    values: list[str] = Field(
        description="Core values that resonate with this audience (e.g., 'family', 'innovation', 'quality')"
    )
    interests: list[str] = Field(
        description="Key interests and hobbies (e.g., 'cooking', 'technology', 'sports')"
    )
    lifestyle: str = Field(
        description="Lifestyle description (e.g., 'family-oriented, health-conscious')"
    )


class PrimaryAudience(BaseModel):
    """Primary target audience profile."""

    demographics: Demographics
    psychographics: Psychographics


class SecondaryAudience(BaseModel):
    """Secondary audience segment with fit assessment."""

    segment: str = Field(
        description="Name/description of the secondary audience segment"
    )
    fit_score: float = Field(
        description="How well the content fits this segment (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        description="Why this segment is a good or partial fit"
    )


class MarketPotential(BaseModel):
    """Market adaptation potential analysis."""

    high_fit_markets: list[str] = Field(
        description="Country codes where content resonates strongly with minimal adaptation"
    )
    adaptation_needed: list[str] = Field(
        default_factory=list,
        description="Country codes requiring cultural adaptation before deployment"
    )
    considerations: list[str] = Field(
        description="Market-specific considerations and recommendations"
    )


class AudienceInsights(BaseModel):
    """Complete audience targeting insights from video analysis.

    This schema defines the structured output for LLM-generated
    audience insights based on video content analysis.
    """

    reasoning: str = Field(
        description="Step-by-step reasoning process used to analyze the video and derive audience insights"
    )
    primary_audience: PrimaryAudience = Field(
        description="Primary target audience profile"
    )
    secondary_audiences: list[SecondaryAudience] = Field(
        default_factory=list,
        description="Additional audience segments with fit scores"
    )
    market_potential: MarketPotential = Field(
        description="Geographic market fit and adaptation recommendations"
    )
    messaging_recommendations: list[str] = Field(
        description="Key messaging strategies to maximize audience resonance"
    )
```

**Why this schema?**
- Matches the existing fallback output structure (easy migration)
- Adds structured reasoning (like other pipeline nodes)
- Provides validation via Pydantic (catches LLM hallucinations)
- Enables type-safe access in downstream code

---

### Step 2: Create Prompt Template

**File**: `data/prompt_templates.json` (add new template)

```json
{
  "slug": "audience-insights",
  "name": "Audience Insights Analysis",
  "category": "analysis",
  "template": "You are an expert marketing analyst specializing in audience segmentation and targeting.\n\nAnalyze the following video content and generate comprehensive audience insights:\n\n## Video Script\n{{ script_scenes | tojson(indent=2) }}\n\n## Visual Style\n- Dominant Colors: {{ dominant_colors }}\n- Average Brightness: {{ avg_brightness }}\n- Lighting: {{ lighting_distribution | tojson }}\n\n## Sentiment Analysis\n- Overall Sentiment: {{ overall_sentiment }}\n- Sentiment Score: {{ sentiment_score }}\n\n## Content Categories\n- Primary Categories: {{ primary_categories }}\n- Category Distribution: {{ category_counts | tojson }}\n\n## Transcription Language\n{{ transcription_language }}\n\n---\n\n## Your Task\n\nAnalyze this video content and provide:\n\n1. **Primary Audience Profile**\n   - Demographics (age, gender, income)\n   - Psychographics (values, interests, lifestyle)\n\n2. **Secondary Audiences**\n   - Additional segments that might engage with this content\n   - Fit scores and reasoning for each\n\n3. **Market Potential**\n   - Countries/regions where content will resonate strongly\n   - Markets requiring cultural adaptation\n   - Market-specific considerations\n\n4. **Messaging Recommendations**\n   - Key messaging strategies to maximize audience resonance\n   - Tone and style recommendations\n\nProvide detailed reasoning for your analysis before presenting the insights.",
  "description": "Analyzes video content to generate audience targeting insights",
  "version": 1,
  "is_active": true
}
```

**Import the template:**
```bash
uv run manage.py import_prompt_templates
```

---

### Step 3: Update Audience Insights Function

**File**: `src/cw/lib/video_analysis/audience_insights.py`

```python
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
                "primary_audience_age": insights["primary_audience"]["demographics"]["age_range"],
                "secondary_audiences_count": len(insights["secondary_audiences"]),
                "high_fit_markets_count": len(insights["market_potential"]["high_fit_markets"]),
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

    # ... (existing fallback implementation remains unchanged) ...
```

---

### Step 4: Update Task to Pass Model Config

**File**: `src/cw/tvspots/tasks.py` (update `analyze_video_task`)

Find the call to `generate_audience_insights()` and add model parameters:

```python
# Before (line ~432):
audience_insights = generate_audience_insights(
    script=script,
    visual_style=visual_style,
    sentiment=sentiment,
    transcription=transcription,
    categories=categories,
)

# After:
from cw.core.models import LLMModel

# Get default model or use Qwen2.5-3B
default_model = LLMModel.objects.filter(is_active=True).first()
model_id = default_model.model_id if default_model else "Qwen/Qwen2.5-3B-Instruct"

audience_insights = generate_audience_insights(
    script=script,
    visual_style=visual_style,
    sentiment=sentiment,
    transcription=transcription,
    categories=categories,
    model_id=model_id,
    load_in_4bit=False,  # Enable if memory is constrained
)
```

---

## Testing

### 1. Unit Test the Schema

```python
# tests/test_audience_insights_schema.py
from cw.lib.video_analysis.schemas import AudienceInsights

def test_audience_insights_schema_validation():
    """Test that the schema validates expected output."""
    data = {
        "reasoning": "The video features family moments...",
        "primary_audience": {
            "demographics": {
                "age_range": "25-45",
                "gender": "all",
                "income_level": "middle to upper-middle"
            },
            "psychographics": {
                "values": ["family", "quality", "convenience"],
                "interests": ["cooking", "home life"],
                "lifestyle": "family-oriented"
            }
        },
        "secondary_audiences": [
            {
                "segment": "Young professionals",
                "fit_score": 0.75,
                "reasoning": "Convenience messaging resonates"
            }
        ],
        "market_potential": {
            "high_fit_markets": ["US", "UK", "DE"],
            "adaptation_needed": ["JP", "KR"],
            "considerations": ["Family messaging works in Western markets"]
        },
        "messaging_recommendations": [
            "Emphasize family togetherness",
            "Highlight convenience"
        ]
    }

    # Should validate without errors
    result = AudienceInsights.model_validate(data)
    assert result.primary_audience.demographics.age_range == "25-45"
```

### 2. Test with Real Video

```bash
# Upload a test video and check logs
tail -f logs/tasks.log | grep -i "audience"

# Should see:
# "Generating audience insights with LLM"
# "Audience insights generation complete"
```

### 3. Validate Output Structure

Check the `VideoProcessingResult.audience_insights` field in Django admin:
- Should have `reasoning` field
- Should have structured `primary_audience` with demographics/psychographics
- Should have `secondary_audiences` list with fit scores
- Should have `market_potential` with country codes
- Should have `messaging_recommendations` list

---

## Benefits of This Approach

### 1. **Type Safety**
```python
insights = generate_audience_insights(...)
age = insights["primary_audience"]["demographics"]["age_range"]  # Type-safe access
```

### 2. **Validation**
- Pydantic catches LLM hallucinations (missing fields, wrong types)
- `fit_score` validated as 0.0-1.0 (can't be negative or >1.0)
- Required fields enforced

### 3. **Structured Reasoning**
- LLM explains its analysis process
- Useful for debugging and improving prompts
- Matches pattern used in adaptation pipeline

### 4. **Graceful Fallback**
- LLM failure → rule-based insights
- No task failure, always produces output

### 5. **Model Flexibility**
- Can switch to better models (Qwen2.5-7B, Claude API)
- Per-video model selection
- 4-bit quantization for memory-constrained environments

---

## Estimated Effort

| Task | Time | Difficulty |
|------|------|------------|
| Define Pydantic schema | 30 min | Easy |
| Create/import prompt template | 15 min | Easy |
| Update audience_insights.py | 45 min | Medium |
| Update task to pass model config | 15 min | Easy |
| Testing and iteration | 1-2 hours | Medium |
| **Total** | **~3 hours** | **Medium** |

---

## Alternative: Use Anthropic API (Simpler)

If you have `ANTHROPIC_API_KEY` set, you could skip structured generation and use:

```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[
        {"role": "user", "content": render_prompt("audience-insights", **context)}
    ],
)

insights = json.loads(response.content[0].text)
```

**Trade-offs:**
- ✅ Simpler (no Outlines, no model loading)
- ✅ Higher quality output (Claude is better than Qwen2.5-3B)
- ❌ Requires API key and internet connection
- ❌ Costs money per request
- ❌ Less validation (no Pydantic schema enforcement)

---

## Recommendation

**For MVP**: Keep rule-based fallback (works fine)

**For Production**: Implement structured generation with Pydantic
- Better quality than rules
- No API costs (local LLM)
- Type-safe, validated output
- Matches existing pipeline patterns

**For Enterprise**: Add Anthropic API as primary, structured generation as fallback
- Best quality insights
- Still works offline/local
- Degradation strategy
