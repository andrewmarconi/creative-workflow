# Implementation Plan: Multi-Model Pipeline

**PRD**: [prd.md](prd.md)
**Issue**: [#26](https://github.com/andrewmarconi/generative-creative-lab/issues/26)

---

## Phase 1: Foundation

Everything in this phase can be built and tested without touching any existing code.

### Step 1.1 — Add LangGraph dependency

**Files**: `pyproject.toml`

- Add `langgraph>=0.2` to project dependencies
- Run `uv sync` to install and verify resolution against existing deps (torch, transformers, outlines, etc.)
- Verify `from langgraph.graph import StateGraph` imports cleanly

**Risk**: LangGraph's `langchain-core` transitive dependency may conflict with existing package versions. Resolve any pins before proceeding.

**Checkpoint**: `uv sync` succeeds, import works.

---

### Step 1.2 — Pydantic schemas

**Files**: `src/cw/lib/pipeline/__init__.py` (empty), `src/cw/lib/pipeline/schemas.py`

Define all Pydantic models and the `PipelineState` TypedDict:

- `ConceptBrief` — core message, emotional beats, narrative structure, themes, cultural assumptions, must-preserve, can-adapt, brand voice
- `CulturalBrief` — market context, substitutions (nested `Substitution`), tone adjustments, pitfalls, opportunities, regulatory notes
- `Substitution` — original, replacement, rationale
- `EvaluationResult` — passed, score, issues (nested `EvaluationIssue`), summary
- `EvaluationIssue` — severity, description, location, suggestion
- `PipelineState` — TypedDict with all input, intermediate, evaluation, and terminal fields per PRD Section 5.2

No imports from `cw.tvspots` or `cw.lib.adaptation` — schemas are self-contained.

**Checkpoint**: Schemas importable, `ConceptBrief.model_json_schema()` produces valid JSON Schema that Outlines can consume.

---

### Step 1.3 — Model loader extraction

**Files**: `src/cw/lib/pipeline/model_loader.py`, `src/cw/lib/adaptation.py` (refactor)

Extract the model loading logic from `AdaptationGenerator` into a shared module:

- `PipelineModelLoader` class with:
  - `__init__(model_id, device, load_in_4bit)` — same signature as `AdaptationGenerator`
  - `_is_model_cached()` — moved from `AdaptationGenerator`
  - `_load_model()` — moved from `AdaptationGenerator`, but generic (no hardcoded `AdaptationOutput` schema)
  - `get_generator(output_schema)` — returns an Outlines `Generator` bound to a specific Pydantic schema
  - `clear_cache()` — moved from `AdaptationGenerator`
  - `switch_model(model_id, load_in_4bit)` — clear cache and reconfigure
- Module-level singleton: `get_model_loader()` (replaces `get_adaptation_generator()` for pipeline use)

Refactor `AdaptationGenerator` to delegate to `PipelineModelLoader` internally so existing single-step path continues to work. The `AdaptationGenerator` becomes a thin wrapper:

```python
class AdaptationGenerator:
    def __init__(self, ...):
        self._loader = PipelineModelLoader(model_id, device, load_in_4bit)

    def _load_model(self):
        self._generator = self._loader.get_generator(AdaptationOutput)

    # adapt() and _build_prompt() unchanged
    # clear_cache() delegates to self._loader.clear_cache()
```

**Checkpoint**: Existing `create_adaptation_task` works exactly as before. `PipelineModelLoader.get_generator(ConceptBrief)` returns a working Outlines generator.

---

### Step 1.4 — Prompt templates

**Files**:
- `src/cw/lib/prompts/concept_extraction.j2`
- `src/cw/lib/prompts/cultural_research.j2`
- `src/cw/lib/prompts/eval_cultural.j2`
- `src/cw/lib/prompts/eval_concept.j2`

Each template follows the existing pattern from `adaptation.j2`:

**concept_extraction.j2**:
- Input variables: `original_json`
- System message: "You are an expert advertising analyst..."
- Instructs the LLM to decompose the script into the `ConceptBrief` schema fields
- Provides the JSON schema as output format specification
- Emphasizes identifying universal vs culture-specific elements

**cultural_research.j2**:
- Input variables: `concept_brief_json`, `target_market_name`, `target_market_rules`, `original_json`
- System message: "You are a cultural research specialist..."
- Instructs the LLM to produce a `CulturalBrief` using the market rules and concept analysis
- Must reference specific elements from the concept brief's `cultural_assumptions` and `can_adapt` lists

**eval_cultural.j2**:
- Input variables: `adapted_script_json`, `cultural_brief_json`, `target_market_rules`
- System message: "You are a cultural compliance reviewer..."
- Instructs the LLM to check script against cultural brief and rules
- Must return `EvaluationResult` with specific issues and actionable suggestions
- Scoring rubric: critical issues = auto-fail, major = fail if >1, minor = pass with notes

**eval_concept.j2**:
- Input variables: `adapted_script_json`, `concept_brief_json`
- System message: "You are a brand strategy reviewer..."
- Instructs the LLM to verify core message, emotional beats, and must-preserve elements survived adaptation
- Same `EvaluationResult` schema and scoring rubric

All templates use `render_prompt()` from `cw.lib.prompts` (existing loader).

**Checkpoint**: Each template renders without error when given test data via `render_prompt()`.

---

## Phase 2: Pipeline Core

Build the graph and nodes. Still no changes to existing models or tasks.

### Step 2.1 — Node functions

**Files**: `src/cw/lib/pipeline/nodes.py`

Implement five node functions, each with the same signature `(state: PipelineState) -> dict`:

**`concept_node(state)`**:
1. Load model via `get_model_loader()` with `state["model_id"]`
2. Get Outlines generator for `ConceptBrief` schema
3. Render `concept_extraction.j2` with `state["original_script"]`
4. Apply chat template formatting (same pattern as `AdaptationGenerator._build_prompt()`)
5. Call generator, parse result
6. Update `AdaptationJob` status to `"concept_analysis"` (by ID from state)
7. Persist `concept_brief` JSON to `AdaptationJob.concept_brief`
8. Return `{"concept_brief": result.model_dump_json(), "status": "concept_analysis"}`

**`culture_node(state)`**:
- Same pattern, uses `cultural_research.j2`, outputs `CulturalBrief`
- Persists to `AdaptationJob.cultural_brief`

**`writer_node(state)`**:
- Uses extended `adaptation.j2` with concept/cultural briefs and optional feedback
- Checks revision counts; if `total_revisions >= 2`, calls `switch_model()` to try alternative
- Uses existing `AdaptationOutput` schema
- Status: `"writing"` on first call, `"revising"` if feedback present

**`cultural_eval_node(state)`**:
- Uses `eval_cultural.j2`, outputs `EvaluationResult`
- If `passed`: returns `{"cultural_feedback": None}`
- If failed: increments `cultural_revision_count`, returns `{"cultural_feedback": result.model_dump_json()}`
- Appends evaluation to `AdaptationJob.evaluation_history`

**`concept_eval_node(state)`**:
- Same pattern as cultural eval, using `eval_concept.j2`

Each node handles its own status update and `AdaptationJob` field persistence as a side-effect. The ORM import is at function level (same pattern as existing `tasks.py`).

**Checkpoint**: Each node function can be called in isolation with a hand-crafted `PipelineState` dict and produces the expected state update.

---

### Step 2.2 — Extend adaptation.j2

**Files**: `src/cw/lib/prompts/adaptation.j2`

Add conditional sections to the existing template. New content goes **before** the "Adaptation Requirements" section:

```jinja2
{% if concept_brief %}
## Concept Analysis
The following concept analysis was extracted from the original script. Your adaptation MUST preserve these elements:
{{ concept_brief }}
{% endif %}

{% if cultural_brief %}
## Cultural Research
The following cultural research was conducted for the target market. Follow these recommendations:
{{ cultural_brief }}
{% endif %}

{% if revision_feedback %}
## Revision Required
Your previous adaptation was reviewed and needs changes. Address ALL of the following issues:
{{ revision_feedback }}
{% endif %}
```

These variables are optional — when absent (single-step path), the template renders exactly as today.

**Checkpoint**: Template renders identically to current output when new variables are not provided. When provided, new sections appear correctly.

---

### Step 2.3 — State helpers

**Files**: `src/cw/lib/pipeline/state.py`

**`build_initial_state(job) -> PipelineState`**:
- Reads `job.origin_version`, `job.target_market`, `job.effective_language`, `job.effective_llm_model`
- Serializes origin version + script rows to dict (same logic as `AdaptationGenerator.adapt()`)
- Returns fully populated `PipelineState` with all intermediate fields set to `None`/`0`

**`save_pipeline_result(job, final_state)`**:
- If `final_state["status"] == "completed"` and `adapted_script` is present:
  - Parse `AdaptationOutput` from `final_state["adapted_script"]`
  - Create `TvSpotVersion` and `TvSpotScriptRow` records (same logic as current `create_adaptation_task`)
  - Set `job.result_version`, `job.status = "completed"`, `job.completed_at`
- If failed:
  - Set `job.status = "failed"`, `job.error_message`
- Always:
  - Persist `job.pipeline_metadata` with timing, revision counts, models used

**`get_alternative_model(language_code) -> Optional[LLMModel]`**:
- Looks up `Language` by code, returns first active `alternative_models` entry
- Returns `None` if no alternatives available

**Checkpoint**: `build_initial_state()` produces a valid `PipelineState` from an existing `AdaptationJob`. `save_pipeline_result()` creates the same `TvSpotVersion` records as the current task.

---

### Step 2.4 — Graph definition

**Files**: `src/cw/lib/pipeline/graph.py`

Build the LangGraph `StateGraph`:

```python
from langgraph.graph import StateGraph, END

def build_adaptation_graph():
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("concept", concept_node)
    graph.add_node("culture", culture_node)
    graph.add_node("writer", writer_node)
    graph.add_node("cultural_eval", cultural_eval_node)
    graph.add_node("concept_eval", concept_eval_node)

    # Linear flow: start → concept → culture → writer
    graph.set_entry_point("concept")
    graph.add_edge("concept", "culture")
    graph.add_edge("culture", "writer")

    # Writer → cultural eval (always)
    graph.add_edge("writer", "cultural_eval")

    # Cultural eval → conditional
    graph.add_conditional_edges("cultural_eval", route_after_cultural_eval, {
        "concept_eval": "concept_eval",
        "writer": "writer",
        "fail": END,
    })

    # Concept eval → conditional
    graph.add_conditional_edges("concept_eval", route_after_concept_eval, {
        "end": END,
        "writer": "writer",
        "fail": END,
    })

    return graph.compile()
```

**Checkpoint**: `build_adaptation_graph()` compiles without error. Graph can be visualized via `graph.get_graph().draw_mermaid()`.

---

### Step 2.5 — Pipeline entry point

**Files**: `src/cw/lib/pipeline/__init__.py`

Wire up `run_adaptation_pipeline(job)` as defined in PRD Section 10:

```python
def run_adaptation_pipeline(job):
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

**Checkpoint**: Can call `run_adaptation_pipeline(job)` with a real `AdaptationJob` and get a completed pipeline run end-to-end. This is the first full integration test.

---

## Phase 3: Integration

Connect the pipeline to the existing system with a feature flag.

### Step 3.1 — Database migration

**Files**: `src/cw/tvspots/models.py`, new migration file

Add to `AdaptationJob`:
- Expand `STATUS_CHOICES` with pipeline phases
- `concept_brief = JSONField(null=True, blank=True)`
- `cultural_brief = JSONField(null=True, blank=True)`
- `evaluation_history = JSONField(default=list, blank=True)`
- `pipeline_metadata = JSONField(default=dict, blank=True)`
- `use_pipeline = BooleanField(default=False)`

Run `uv run manage.py makemigrations tvspots && uv run manage.py migrate`.

**Checkpoint**: Migration applies cleanly. Existing jobs unaffected. New fields visible in Django shell.

---

### Step 3.2 — Task integration with feature flag

**Files**: `src/cw/tvspots/tasks.py`

Update `create_adaptation_task` to branch on the `use_pipeline` flag:

```python
@shared_task(bind=True, name="cw.tvspots.tasks.create_adaptation_task")
def create_adaptation_task(self, adaptation_job_id):
    from cw.tvspots.models import AdaptationJob

    job = AdaptationJob.objects.get(id=adaptation_job_id)

    if job.use_pipeline:
        from cw.lib.pipeline import run_adaptation_pipeline
        try:
            run_adaptation_pipeline(job)
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])
    else:
        # Existing single-step path — unchanged
        _run_single_step_adaptation(job)
```

Extract the current task body into `_run_single_step_adaptation(job)` as a local helper to keep the diff clean.

**Checkpoint**: Jobs with `use_pipeline=False` behave identically to today. Jobs with `use_pipeline=True` run through the LangGraph pipeline.

---

### Step 3.3 — Admin UI updates

**Files**: `src/cw/tvspots/admin.py`

Update `AdaptationJobAdmin`:
- Add `use_pipeline` to the create form fields
- Add read-only display of `concept_brief`, `cultural_brief`, `evaluation_history`, `pipeline_metadata` using Django Unfold tabbed inlines or fieldsets
- Update `list_display` to show pipeline status phases
- Update `list_filter` to include `use_pipeline`

**Checkpoint**: Can create a job with `use_pipeline=True` from admin. Can view intermediate outputs on completed pipeline jobs.

---

## Phase 4: Validation

### Step 4.1 — End-to-end test with existing data

Run the pipeline against an existing TV spot and market:

1. Pick a `TvSpot` with a known-good origin version
2. Create an `AdaptationJob` with `use_pipeline=True`
3. Let it run through the full pipeline
4. Verify:
   - `concept_brief` is populated and coherent
   - `cultural_brief` references market rules correctly
   - `adapted_script` preserves core message (per concept brief)
   - Evaluation loops fired (check `evaluation_history`)
   - Final `TvSpotVersion` and `TvSpotScriptRow` records created
   - `pipeline_metadata` contains timing and model info

### Step 4.2 — Comparison test

For the same TV spot and market, create two jobs:
1. `use_pipeline=False` — single-step (baseline)
2. `use_pipeline=True` — pipeline

Compare output quality side-by-side in admin.

### Step 4.3 — Evaluation loop exercise

Create a test scenario likely to trigger revision loops:
- Pick a culturally sensitive market (e.g., MENA, Japan)
- Use a script with Western-specific references
- Verify that:
  - Cultural evaluator flags issues
  - Writer node revises with feedback
  - Revision count increments
  - Alternative model fallback triggers on third retry (if applicable)
  - Pipeline either succeeds after revision or fails gracefully at max retries

### Step 4.4 — Model fallback test

Configure a `Language` with both `primary_model` and `alternative_models`. Run a pipeline job where the primary model produces culturally misaligned output. Verify:
- First two revisions use primary model
- Third revision switches to alternative
- `pipeline_metadata` records the model switch

---

## Dependency Graph

```
Phase 1 (Foundation) — no existing code changes
  1.1  Add langgraph dep
  1.2  Pydantic schemas           ← depends on 1.1 (for dev environment)
  1.3  Model loader extraction    ← independent of 1.2
  1.4  Prompt templates           ← independent of 1.2, 1.3

Phase 2 (Pipeline Core) — new files only, no existing code changes except adaptation.j2
  2.1  Node functions             ← depends on 1.2, 1.3, 1.4
  2.2  Extend adaptation.j2       ← depends on 1.4
  2.3  State helpers              ← depends on 1.2
  2.4  Graph definition           ← depends on 2.1
  2.5  Pipeline entry point       ← depends on 2.3, 2.4

Phase 3 (Integration) — modifies existing code
  3.1  Database migration         ← independent
  3.2  Task integration           ← depends on 2.5, 3.1
  3.3  Admin UI                   ← depends on 3.1

Phase 4 (Validation) — testing only
  4.1–4.4                         ← depends on 3.2
```

Steps 1.2, 1.3, and 1.4 can be done in parallel. Steps 2.1 and 2.2 can be done in parallel. Step 3.1 can be done in parallel with Phase 2.

---

## Risk Mitigations

| Risk | Mitigation |
|---|---|
| LangGraph dependency conflicts | Step 1.1 resolves this first, before any code is written |
| Model loading overhead (5 LLM calls per pipeline run) | All nodes share the singleton `PipelineModelLoader` — model loads once, generator schema swaps are cheap |
| Outlines generator schema switching | Verify in Step 1.3 that `get_generator(schema)` can be called multiple times with different schemas on the same loaded model |
| Pipeline timeout on Celery worker | Existing 3600s hard limit should be sufficient for 5 LLM calls. Add per-node timing to `pipeline_metadata` to identify bottlenecks |
| Evaluation loops never converge | Max 3 retries per evaluator is hard-coded in conditional edges. Worst case: 3 cultural + 3 concept = 6 extra writer calls before failure |
| Prompt template quality | Templates are the most likely iteration point. Phase 4 will likely require multiple rounds of template refinement |
| Breaking existing single-step path | Feature flag (`use_pipeline`) ensures zero risk. Single-step code path is untouched until cutover |
