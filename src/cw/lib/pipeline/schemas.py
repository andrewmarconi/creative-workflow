"""Pydantic schemas and PipelineState TypedDict for the multi-agent adaptation pipeline."""

from __future__ import annotations

from typing import Optional, TypedDict

from pydantic import BaseModel, Field


class Substitution(BaseModel):
    """A single cultural substitution recommendation."""

    original: str = Field(description="Original cultural reference or element")
    replacement: str = Field(description="Suggested replacement for target market")
    rationale: str = Field(description="Why this substitution is recommended")


class ConceptBrief(BaseModel):
    """Output of the concept extraction node — decomposes the original script."""

    reasoning: str = Field(
        description="Step-by-step thinking process used to analyze the script and extract key concepts"
    )
    core_message: str = Field(description="Primary selling proposition and key message")
    emotional_beats: list[str] = Field(description="Key emotional moments in the narrative")
    narrative_structure: str = Field(description="Story arc: setup, conflict, resolution")
    themes: list[str] = Field(description="Universal and culture-specific themes")
    cultural_assumptions: list[str] = Field(
        description="Cultural assumptions embedded in the original script"
    )
    must_preserve: list[str] = Field(
        description="Non-negotiable elements that must survive adaptation"
    )
    can_adapt: list[str] = Field(
        description="Elements that can be culturally adapted or substituted"
    )
    brand_voice: str = Field(description="Tone, style, and brand personality characteristics")


class CulturalBrief(BaseModel):
    """Output of the cultural research node — market-specific adaptation guidance."""

    reasoning: str = Field(
        description="Step-by-step thinking about the target market's cultural context, values, sensitivities, and how the original concept should be adapted"
    )
    market_context: str = Field(description="Summary of target market cultural context")
    substitutions: list[Substitution] = Field(
        description="Recommended cultural reference substitutions"
    )
    tone_adjustments: str = Field(
        description="How to adjust tone and style for the target market"
    )
    pitfalls: list[str] = Field(description="Cultural pitfalls and sensitivities to avoid")
    opportunities: list[str] = Field(
        description="Cultural opportunities to leverage for resonance"
    )
    regulatory_notes: str = Field(
        default="", description="Regulatory or compliance considerations"
    )


class EvaluationIssue(BaseModel):
    """A single issue found during evaluation."""

    severity: str = Field(description="Issue severity: 'critical', 'major', or 'minor'")
    description: str = Field(description="Description of the issue")
    location: str = Field(description="Where in the script the issue occurs")
    suggestion: str = Field(description="Actionable suggestion to fix the issue")


class EvaluationResult(BaseModel):
    """Output of an evaluation node — quality assessment of an adapted script."""

    reasoning: str = Field(
        description="Step-by-step evaluation process explaining what was checked, what issues were found (if any), and how the score was determined"
    )
    passed: bool = Field(description="Whether the adaptation passes this evaluation")
    score: float = Field(description="Quality score from 0.0 to 1.0")
    issues: list[EvaluationIssue] = Field(
        default_factory=list, description="List of issues found"
    )
    summary: str = Field(description="Brief summary of the evaluation result")


class PipelineState(TypedDict, total=False):
    """State passed between LangGraph nodes in the adaptation pipeline.

    Input fields are set at pipeline start. Intermediate fields are populated
    by nodes as the pipeline progresses. Evaluation fields track quality gates
    and revision loops. Terminal fields hold the final output.
    """

    # --- Input fields (set once at pipeline start) ---
    job_id: int
    model_id: str
    load_in_4bit: bool
    model_config: dict  # {node_key: {"model_id": str, "load_in_4bit": bool}}
    original_script: str  # JSON string of the origin version data
    target_market_name: str
    target_market_code: str
    target_market_rules: str  # Markdown-formatted market rules
    target_market_language: str  # Language code (e.g., "es-MX")
    language_code: str  # ISO language code for alternative model lookups
    num_script_rows: int
    brand_guidelines: str  # Brand voice/values/guidelines from Campaign

    # --- Intermediate fields (populated by nodes) ---
    concept_brief: Optional[str]  # JSON string of ConceptBrief
    cultural_brief: Optional[str]  # JSON string of CulturalBrief
    adapted_script: Optional[str]  # JSON string of AdaptationOutput

    # --- Evaluation fields ---
    format_feedback: Optional[str]  # JSON string of EvaluationResult, or None if passed
    cultural_feedback: Optional[str]  # JSON string of EvaluationResult, or None if passed
    concept_feedback: Optional[str]  # JSON string of EvaluationResult, or None if passed
    brand_feedback: Optional[str]  # JSON string of EvaluationResult, or None if passed
    format_revision_count: int
    cultural_revision_count: int
    concept_revision_count: int
    brand_revision_count: int

    # --- Terminal fields ---
    status: str  # Current pipeline status
    error_message: Optional[str]
