"""Pydantic schemas for video analysis outputs."""

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    """Demographic profile for audience segment."""

    age_range: str = Field(description="Target age range (e.g., '25-45', '18-34')")
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
    reasoning: str = Field(description="Why this segment is a good or partial fit")


class MarketPotential(BaseModel):
    """Market adaptation potential analysis."""

    high_fit_markets: list[str] = Field(
        description="Country codes where content resonates strongly with minimal adaptation"
    )
    adaptation_needed: list[str] = Field(
        default_factory=list,
        description="Country codes requiring cultural adaptation before deployment",
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
        description="Additional audience segments with fit scores",
    )
    market_potential: MarketPotential = Field(
        description="Geographic market fit and adaptation recommendations"
    )
    messaging_recommendations: list[str] = Field(
        description="Key messaging strategies to maximize audience resonance"
    )
