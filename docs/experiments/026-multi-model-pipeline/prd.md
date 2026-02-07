# PRD: Multi-Model Pipeline for TV Spot Adaptation

**Issue**: [#26 — Multi-Model Pipeline for TV Spot Localization & Adaptation](https://github.com/andrewmarconi/generative-creative-lab/issues/26)
**Status**: Draft
**Author**: Claude Code

---

## 1. Problem Statement

The current adaptation system is single-step: one Celery task loads one LLM, generates one output, and saves it. There is no concept analysis, no cultural evaluation, and no revision loop. If the output is poor, the user must manually re-run the job and hope for better results.

The quality gap shows up in three ways:
1. **No concept preservation check** — the LLM may drift from the original creative intent
2. **No cultural validation** — culturally inappropriate content passes through unchecked
3. **No iterative refinement** — first-pass output is final output, regardless of quality

## 2. Goal

Build a multi-agent pipeline using **LangGraph** that orchestrates three specialized sub-agents (Concept, Culture, Writer) under a supervisor, with evaluation loops that catch and correct quality issues before producing a final adaptation. All inference runs on **local HuggingFace models** — no external APIs.

## 3. Non-Goals

- External API calls (Anthropic, OpenAI, etc.)
- Per-node model override fields on `AdaptationJob` (future extension)
- Real-time streaming of intermediate outputs to the admin UI
- Multi-modal input (video frame analysis)
- Parallel multi-market execution within a single job

## 4. Existing Infrastructure

The following components exist and will be reused as-is or extended:

| Component | Location | Reuse |
|---|---|---|
| `LLMModel` | `src/cw/core/models.py` | As-is — model registry with `model_id`, `load_in_4bit` |
| `Language` | `src/cw/core/models.py` | As-is — `primary_model` + `alternative_models` per language |
| `AdaptationMarket` | `src/cw/tvspots/models.py` | As-is — cultural rules via `rules_as_markdown()` |
| `AdaptationJob` | `src/cw/tvspots/models.py` | Extended — new status values, new fields for pipeline artifacts |
| `AdaptationGenerator` | `src/cw/lib/adaptation.py` | Refactored — becomes the Writer node's core logic |
| `AdaptationOutput` | `src/cw/lib/adaptation.py` | As-is — Pydantic schema for final adapted script |
| `adaptation.j2` | `src/cw/lib/prompts/adaptation.j2` | Becomes the Writer node's prompt template |
| `create_adaptation_task` | `src/cw/tvspots/tasks.py` | Refactored — launches LangGraph instead of calling generator directly |
| `data/core_data.json` | 8 LLM models, 36 languages | As-is — drives model selection |
| `data/market_profiles.json` | 18 markets with cultural rules | As-is — feeds Culture agent |

### Model Selection Hierarchy (unchanged)

```
AdaptationJob.llm_model (explicit override)
  → Language.primary_model (language default)
    → Fallback: Qwen/Qwen2.5-3B-Instruct
```

The `effective_llm_model` property on `AdaptationJob` continues to resolve this. All nodes in the pipeline use the same resolved model for a given job. On evaluation failure retries, the pipeline may switch to a `Language.alternative_models` entry.

## 5. Pipeline Architecture

### 5.1 Graph Topology

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Concept   │  → produces ConceptBrief
                    │    Node     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Culture   │  → produces CulturalBrief
                    │    Node     │
                    └──────┬──────┘
                           │
               ┌───────────▼───────────┐
               │      Writer Node      │  → produces AdaptedScript
               └───────────┬───────────┘
                           │
               ┌───────────▼───────────┐
            ┌──│  Cultural Evaluator   │──┐
            │  └───────────────────────┘  │
            │ fail (max 3)          pass  │
            │                             │
            ▼                             ▼
     ┌─────────────┐          ┌───────────────────────┐
     │ Writer Node │─────────►│  Concept Evaluator    │──┐
     │ (revision)  │          └───────────────────────┘  │
     └─────────────┘           │ fail (max 3)      pass  │
            ▲                  │                          │
            └──────────────────┘                          ▼
                                                   ┌───────────┐
                                                   │    END     │
                                                   └───────────┘

     If either evaluator exceeds 3 revisions → FAIL
```

### 5.2 Graph State

A single `PipelineState` TypedDict flows through all nodes:

```python
from typing import TypedDict, Optional

class PipelineState(TypedDict):
    # --- Inputs (set at START, immutable) ---
    adaptation_job_id: int
    original_script: dict            # Serialized origin TvSpotVersion + rows
    target_market_name: str
    target_market_code: str
    target_market_rules: str         # Markdown from rules_as_markdown()
    language_code: str
    language_name: str
    model_id: str                    # Resolved from effective_llm_model
    load_in_4bit: bool

    # --- Intermediate outputs (set by nodes) ---
    concept_brief: Optional[str]     # From Concept node
    cultural_brief: Optional[str]    # From Culture node
    adapted_script: Optional[str]    # JSON string of AdaptationOutput

    # --- Evaluation state ---
    cultural_feedback: Optional[str]
    concept_feedback: Optional[str]
    cultural_revision_count: int     # Starts at 0, max 3
    concept_revision_count: int      # Starts at 0, max 3
    current_model_id: str            # May change on fallback

    # --- Terminal state ---
    status: str                      # Current pipeline phase
    error_message: Optional[str]
```

### 5.3 Node Definitions

Each node is a Python function that receives `PipelineState`, calls the LLM via Outlines, and returns a partial state update. All nodes share the same model loading infrastructure from `AdaptationGenerator`.

#### Concept Node

**Purpose**: Extract the core creative concept, themes, and adaptation constraints from the original script.

**Input from state**: `original_script`
**Output to state**: `concept_brief`
**Pydantic schema**: `ConceptBrief`

```python
class ConceptBrief(BaseModel):
    core_message: str           # Primary selling proposition
    emotional_beats: list[str]  # Key emotional moments
    narrative_structure: str    # Setup/conflict/resolution description
    universal_themes: list[str] # Themes that translate across cultures
    cultural_assumptions: list[str]  # Culture-specific elements in original
    must_preserve: list[str]    # Non-negotiable elements
    can_adapt: list[str]        # Elements open to cultural adaptation
    brand_voice: str            # Tone and style requirements
```

**New template**: `src/cw/lib/prompts/concept_extraction.j2`
**Status update**: `AdaptationJob.status = "concept_analysis"`

#### Culture Node

**Purpose**: Produce cultural research and recommendations for the target market, informed by the concept brief and the market's structured rules.

**Input from state**: `concept_brief`, `target_market_rules`, `original_script`
**Output to state**: `cultural_brief`
**Pydantic schema**: `CulturalBrief`

```python
class CulturalBrief(BaseModel):
    market_context: str               # Summary of target market
    substitutions: list[Substitution] # Cultural reference replacements
    tone_adjustments: list[str]       # Recommended tone changes
    pitfalls: list[str]               # Things to avoid
    opportunities: list[str]          # Localization opportunities
    regulatory_notes: list[str]       # Legal/regulatory considerations

class Substitution(BaseModel):
    original: str       # Element from the original script
    replacement: str    # Culturally appropriate replacement
    rationale: str      # Why this substitution works
```

**New template**: `src/cw/lib/prompts/cultural_research.j2`
**Status update**: `AdaptationJob.status = "cultural_analysis"`

#### Writer Node

**Purpose**: Generate the adapted script using the concept brief, cultural brief, and original script. On revision, receives evaluator feedback.

**Input from state**: `concept_brief`, `cultural_brief`, `original_script`, plus optionally `cultural_feedback` or `concept_feedback`
**Output to state**: `adapted_script`
**Pydantic schema**: `AdaptationOutput` (existing)

**Template**: `src/cw/lib/prompts/adaptation.j2` (existing, extended to accept concept/cultural briefs and evaluator feedback)
**Status update**: `AdaptationJob.status = "writing"` or `"revising"`

#### Cultural Evaluator Node

**Purpose**: Evaluate the adapted script against the cultural brief. Returns pass/fail with feedback.

**Input from state**: `adapted_script`, `cultural_brief`, `target_market_rules`
**Output to state**: `cultural_feedback` (if fail), clears feedback (if pass)
**Pydantic schema**: `EvaluationResult`

```python
class EvaluationResult(BaseModel):
    passed: bool
    score: float                    # 0.0–1.0 confidence
    issues: list[EvaluationIssue]   # Empty if passed
    summary: str                    # Brief overall assessment

class EvaluationIssue(BaseModel):
    severity: str       # "critical", "major", "minor"
    description: str    # What the issue is
    location: str       # Which part of the script
    suggestion: str     # How to fix it
```

**New template**: `src/cw/lib/prompts/eval_cultural.j2`
**Status update**: `AdaptationJob.status = "cultural_evaluation"`

#### Concept Evaluator Node

**Purpose**: Evaluate the adapted script against the concept brief to ensure the core message is preserved.

**Input from state**: `adapted_script`, `concept_brief`
**Output to state**: `concept_feedback` (if fail), clears feedback (if pass)
**Pydantic schema**: `EvaluationResult` (same as Cultural Evaluator)

**New template**: `src/cw/lib/prompts/eval_concept.j2`
**Status update**: `AdaptationJob.status = "concept_evaluation"`

### 5.4 Conditional Edges

```python
def route_after_cultural_eval(state: PipelineState) -> str:
    if state["cultural_feedback"] is None:
        return "concept_evaluator"  # Passed — move to next eval
    if state["cultural_revision_count"] >= 3:
        return "fail"               # Exhausted retries
    return "writer"                 # Revise

def route_after_concept_eval(state: PipelineState) -> str:
    if state["concept_feedback"] is None:
        return "end"                # Passed — done
    if state["concept_revision_count"] >= 3:
        return "fail"               # Exhausted retries
    return "writer"                 # Revise
```

### 5.5 Model Fallback on Retry

When the Writer node is invoked for a third revision (either cultural or concept), the pipeline switches to the first available `Language.alternative_models` entry:

```python
def writer_node(state: PipelineState) -> dict:
    total_revisions = state["cultural_revision_count"] + state["concept_revision_count"]
    if total_revisions >= 2 and state["current_model_id"] == state["model_id"]:
        # Try an alternative model for a fresh perspective
        alternative = get_alternative_model(state["language_code"])
        if alternative:
            state_update["current_model_id"] = alternative.model_id
    ...
```

## 6. Data Model Changes

### 6.1 AdaptationJob — New Status Values

Extend the `STATUS_CHOICES` on `AdaptationJob`:

```python
STATUS_CHOICES = [
    # Existing
    ("pending", "Pending"),
    ("processing", "Processing"),        # Keep for backwards compat
    ("completed", "Completed"),
    ("failed", "Failed"),
    # New — pipeline phases
    ("concept_analysis", "Concept Analysis"),
    ("cultural_analysis", "Cultural Analysis"),
    ("writing", "Writing"),
    ("cultural_evaluation", "Cultural Evaluation"),
    ("concept_evaluation", "Concept Evaluation"),
    ("revising", "Revising"),
]
```

### 6.2 AdaptationJob — New Fields

```python
# Pipeline intermediate outputs (stored for inspection and debugging)
concept_brief = models.JSONField(
    null=True, blank=True,
    help_text="Concept extraction output from the Concept agent.",
)
cultural_brief = models.JSONField(
    null=True, blank=True,
    help_text="Cultural research output from the Culture agent.",
)
evaluation_history = models.JSONField(
    default=list, blank=True,
    help_text="List of evaluation results from review cycles.",
)
pipeline_metadata = models.JSONField(
    default=dict, blank=True,
    help_text="Pipeline execution metadata (models used, timings, revision counts).",
)
```

These fields allow:
- **Inspection**: View the concept and cultural briefs in Django admin
- **Debugging**: See why evaluators rejected a script and what feedback was given
- **Analytics**: Track which models were used, how many revisions occurred, timing per phase

### 6.3 No New Models Required

All pipeline state lives in `PipelineState` (in-memory during execution) and is persisted to the existing `AdaptationJob` fields above. The final output continues to create `TvSpotVersion` + `TvSpotScriptRow` records exactly as today.

## 7. Separation of Concerns

All pipeline logic lives in `cw.lib`. The Django apps (`cw.tvspots`, `cw.core`) own only models, admin UI, and thin Celery task entry points.

```
cw.lib.pipeline/          ← All orchestration, node logic, state management
cw.lib.prompts/           ← All Jinja2 prompt templates
cw.lib.adaptation         ← Existing single-step generator (kept for backwards compat)

cw.tvspots.models         ← ORM models only (AdaptationJob, TvSpotVersion, etc.)
cw.tvspots.admin          ← Admin UI only (display, forms, actions)
cw.tvspots.tasks          ← Thin Celery entry points — delegate immediately to cw.lib
cw.core.models            ← ORM models only (LLMModel, Language)
```

The Celery task in `cw.tvspots.tasks` does three things and nothing more:
1. Load the `AdaptationJob` from the database
2. Call `cw.lib.pipeline.run_adaptation_pipeline(job)`
3. Handle the top-level try/except for task failure

All state building, graph execution, result persistence, and status updates are handled within `cw.lib.pipeline`. This keeps the pipeline testable independently of Django's task infrastructure and reusable if the entry point changes (e.g., management command, API endpoint).

## 8. New Files

| File | Purpose |
|---|---|
| `src/cw/lib/pipeline/__init__.py` | Package init, exports `run_adaptation_pipeline()` |
| `src/cw/lib/pipeline/graph.py` | LangGraph `StateGraph` definition with nodes and edges |
| `src/cw/lib/pipeline/nodes.py` | Node functions (concept, culture, writer, evaluators) |
| `src/cw/lib/pipeline/schemas.py` | Pydantic schemas (`ConceptBrief`, `CulturalBrief`, `EvaluationResult`, `PipelineState`) |
| `src/cw/lib/pipeline/state.py` | `build_initial_state(job)` and `save_pipeline_result(job, state)` |
| `src/cw/lib/pipeline/model_loader.py` | Shared model loading logic (extracted from `AdaptationGenerator`) |
| `src/cw/lib/prompts/concept_extraction.j2` | Concept node prompt template |
| `src/cw/lib/prompts/cultural_research.j2` | Culture node prompt template |
| `src/cw/lib/prompts/eval_cultural.j2` | Cultural evaluator prompt template |
| `src/cw/lib/prompts/eval_concept.j2` | Concept evaluator prompt template |

## 9. Modified Files

| File | Change |
|---|---|
| `src/cw/tvspots/models.py` | New status choices + JSON fields on `AdaptationJob` |
| `src/cw/tvspots/tasks.py` | `create_adaptation_task` delegates to `cw.lib.pipeline.run_adaptation_pipeline()` |
| `src/cw/tvspots/admin.py` | Display new fields (concept_brief, cultural_brief, evaluation_history) |
| `src/cw/lib/prompts/adaptation.j2` | Extended to accept concept_brief, cultural_brief, and evaluator feedback |
| `src/cw/lib/adaptation.py` | Extract model loading into `pipeline/model_loader.py`; keep for backwards compat |
| `pyproject.toml` | Add `langgraph` dependency |

## 10. Task Integration

The Celery task is a thin entry point that delegates to `cw.lib.pipeline`:

```python
# cw/tvspots/tasks.py — thin entry point
@shared_task(bind=True, name="cw.tvspots.tasks.create_adaptation_task")
def create_adaptation_task(self, adaptation_job_id):
    from cw.tvspots.models import AdaptationJob
    from cw.lib.pipeline import run_adaptation_pipeline

    job = AdaptationJob.objects.get(id=adaptation_job_id)
    try:
        run_adaptation_pipeline(job)
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
```

```python
# cw/lib/pipeline/__init__.py — all logic lives here
def run_adaptation_pipeline(job):
    """Run the full multi-agent adaptation pipeline for an AdaptationJob.

    Handles state building, graph execution, status updates, and
    result persistence. The caller only needs to handle top-level exceptions.
    """
    from .state import build_initial_state, save_pipeline_result
    from .graph import build_adaptation_graph

    job.status = "processing"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    initial_state = build_initial_state(job)
    graph = build_adaptation_graph()
    final_state = graph.invoke(initial_state)

    save_pipeline_result(job, final_state)
```

The graph runs **synchronously** inside the Celery worker. Since the worker uses `solo` pool (single-threaded, GPU-safe), this is consistent with the existing architecture.

## 11. Prompt Templates

### 10.1 Concept Extraction (`concept_extraction.j2`)

Receives the original script JSON and instructs the LLM to decompose it into themes, narrative structure, cultural assumptions, and adaptation constraints. Output must match `ConceptBrief` schema.

### 10.2 Cultural Research (`cultural_research.j2`)

Receives the concept brief and market rules. Instructs the LLM to map cultural context, identify substitutions, flag pitfalls, and recommend tone adjustments. Output must match `CulturalBrief` schema.

### 10.3 Adaptation (`adaptation.j2` — existing, extended)

Receives concept brief, cultural brief, original script, and optionally evaluator feedback from prior revision. The existing template structure is preserved; new sections are added conditionally:

```jinja2
{% if concept_brief %}
## Concept Brief
{{ concept_brief }}
{% endif %}

{% if cultural_brief %}
## Cultural Brief
{{ cultural_brief }}
{% endif %}

{% if revision_feedback %}
## Revision Required
The previous adaptation was rejected. Address the following:
{{ revision_feedback }}
{% endif %}
```

### 10.4 Evaluation Templates (`eval_cultural.j2`, `eval_concept.j2`)

Each receives the adapted script and the relevant brief. Instructs the LLM to score alignment, identify issues by severity, and provide actionable suggestions. Output must match `EvaluationResult` schema.

## 12. Admin UI Changes

### AdaptationJob Detail View

- **Status display**: Show the current pipeline phase with a progress indicator
- **Concept Brief tab**: Rendered JSON of the concept extraction output
- **Cultural Brief tab**: Rendered JSON of the cultural research output
- **Evaluation History tab**: Chronological list of evaluation results with pass/fail, scores, and feedback
- **Pipeline Metadata tab**: Models used per node, timing per phase, revision counts

All new fields use Django Unfold's tabbed interface pattern already established in the codebase.

## 13. Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing ...
    "langgraph>=0.2",
]
```

`langgraph` depends on `langchain-core` but does **not** require `langchain` or any provider-specific packages. All LLM calls continue to use the existing Outlines + HuggingFace Transformers stack.

## 14. Migration Plan

1. **Database migration**: Add new fields to `AdaptationJob` (status choices, JSON fields). Non-breaking — all new fields are nullable or have defaults.
2. **Backwards compatibility**: The existing `AdaptationGenerator.adapt()` method and `create_adaptation_task` continue to work during development. The pipeline is opt-in until validated.
3. **Feature flag**: Add a `use_pipeline` boolean field on `AdaptationJob` (default `False`). When `True`, the task uses the LangGraph pipeline. When `False`, it uses the existing single-step generator. This allows side-by-side comparison.
4. **Cutover**: Once the pipeline is validated, flip the default to `True` and deprecate the single-step path.

## 15. Success Criteria

- Pipeline produces higher-quality adaptations than single-step (measured by human review)
- Evaluation loops catch and correct cultural/concept issues in at least 80% of cases
- Full pipeline completes in under 10 minutes per market on available hardware
- Zero external API calls — all inference runs locally
- Existing single-step adaptation continues to work unaffected during rollout
- Intermediate outputs (concept brief, cultural brief, evaluation feedback) are visible in admin

## 16. Implementation Order

1. **Pydantic schemas** (`pipeline/schemas.py`) — `ConceptBrief`, `CulturalBrief`, `EvaluationResult`, `PipelineState`
2. **Model loader extraction** (`pipeline/model_loader.py`) — shared model loading from `AdaptationGenerator`
3. **Prompt templates** — `concept_extraction.j2`, `cultural_research.j2`, `eval_cultural.j2`, `eval_concept.j2`
4. **Node functions** (`pipeline/nodes.py`) — each node loads model, renders template, calls Outlines, returns state update
5. **Graph definition** (`pipeline/graph.py`) — `StateGraph` with nodes, edges, conditional routing
6. **Database migration** — new fields on `AdaptationJob`
7. **Task integration** — update `create_adaptation_task` with `use_pipeline` flag
8. **Admin UI** — display intermediate outputs in tabbed detail view
9. **Extend `adaptation.j2`** — accept concept/cultural briefs and revision feedback
10. **Testing and validation** — run pipeline against existing adaptations, compare quality
