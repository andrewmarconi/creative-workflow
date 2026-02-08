# Multi-Model Pipeline: Implementation Analysis

## Current Architecture

The existing adaptation system is **single-step and linear**: one Celery task calls one Qwen model via Outlines, produces a validated Pydantic output, done. No loops, no evaluation, no multi-agent coordination.

The spec describes a **multi-agent supervisor pattern** with:
- A **Supervisor Agent** orchestrating three specialized sub-agents (Concept, Culture, Writer)
- **Sequential phases** with structured handoffs between agents
- **Evaluation loops** with max 3 revision cycles per alignment check
- **Status tracking** back to Django throughout the flow
- **Failure handling** when revision limits are exceeded

## Existing Infrastructure to Reuse

The codebase already has a rich model selection and cultural configuration system that maps directly onto the multi-agent pipeline's needs.

### LLMModel + Language Configuration

**`Language` model** provides a per-language model selection hierarchy:
- `primary_model` (FK to `LLMModel`) — default model for that language
- `alternative_models` (M2M to `LLMModel`) — fallback/alternative models
- `get_all_models()` — returns primary + alternatives as a queryset

**8 local HuggingFace models** already configured in `data/core_data.json`:

| Model | Strengths |
|---|---|
| Qwen/Qwen2.5-7B-Instruct | Strong multilingual, best for CJK |
| Qwen/Qwen2.5-3B-Instruct | Lightweight default |
| CohereForAI/aya-expanse-8b | 23-language multilingual |
| google/gemma-2-9b-it | Slovenian, Swahili, Uzbek |
| meta-llama/Llama-3.2-3B-Instruct | Hindi, Thai |
| mistralai/Mistral-7B-Instruct-v0.3 | Excels with German |
| microsoft/Phi-3.5-mini-instruct | Nordic/European |
| facebook/nllb-200-1.3B | Translation-focused, low-resource fallback |

**36 languages** mapped to primary + alternative models, covering Arabic, CJK, European, South/Southeast Asian, and African language families.

### AdaptationMarket + Cultural Rules

**18 adaptation markets** defined in `data/market_profiles.json`, each with structured `rules` (JSON with headings + points arrays) covering:
- Language segmentation guidelines
- Tone and register norms
- Cultural considerations
- Regulatory requirements
- Representation guidance

The `AdaptationMarket.rules_as_markdown()` method already renders these into LLM-friendly prompt content.

### Existing Model Selection Hierarchy

`AdaptationJob` already resolves models through a cascading override:

```
Job-level override (llm_model field)
  → Language primary_model
    → Fallback default (Qwen/Qwen2.5-3B-Instruct)
```

The `effective_llm_model` property on `AdaptationJob` encapsulates this logic. The `AdaptationGenerator.adapt()` method checks if a model switch is needed between jobs and clears/reloads the cache accordingly.

### Structured Output via Outlines

All LLM calls use Outlines + Pydantic schemas, guaranteeing valid JSON output regardless of which local model is loaded. This eliminates the need for output parser frameworks.

## How This Maps to Multi-Agent Nodes

The existing `Language.primary_model` / `alternative_models` pattern can drive per-node model selection. Each agent node uses the language's primary model by default, with alternatives available for fallback or retry with a different model.

### Node-Level Model Resolution

```
For each agent node (Concept, Culture, Writer, Evaluator):
  1. Use Language.primary_model (default — no config needed)
  2. On failure or low-quality output → try Language.alternative_models
  3. Supervisor tracks which model was used per node for the final report
```

This means model selection is **automatic and language-aware** out of the box. Japanese adaptations route to Qwen 2.5 7B. German routes to Mistral. Hindi routes to Llama 3.2. All without per-job configuration.

### Per-Node Model Overrides (Future Extension)

The existing `AdaptationJob.llm_model` override could be extended to per-node granularity if needed:

```python
# Possible extension — not required for v1
class AdaptationJob(models.Model):
    llm_model = ...              # Global override (existing)
    concept_model = ...          # Override for concept node only
    writer_model = ...           # Override for writer node only
```

For v1, the single `llm_model` override applies to all nodes. The `Language.primary_model` default handles the common case.

### Fallback Strategy During Evaluation Loops

When an evaluation loop rejects a script and requests revision:

1. **First retry** — same model, revised prompt with evaluator feedback
2. **Second retry** — same model, further revised prompt
3. **Third retry (optional)** — switch to an `alternative_model` for a different "perspective"
4. **Exhausted** — fail the job with collected feedback

This leverages `Language.alternative_models` as a natural escalation path without introducing external APIs.

## Recommended Approaches

### 1. LangGraph (Recommended)

LangGraph is specifically designed for what the spec describes:

- **Stateful, cyclical graphs** — The evaluation loops with max 3 revisions map directly to LangGraph's conditional edges and cycle support
- **Supervisor pattern** — First-class support for a supervisor node routing to sub-agent nodes (Concept, Culture, Writer)
- **State management** — Built-in state that accumulates across nodes, perfect for passing concept briefs → cultural briefs → scripts between phases
- **Checkpointing** — Can persist state to the existing PostgreSQL, enabling resume-after-failure
- **Human-in-the-loop** — Supports interruption points where a human can review before continuing

**Fit with existing architecture:**
- Celery task launches a LangGraph graph execution
- Each node uses `AdaptationGenerator` with the resolved local model (via `Language.primary_model`)
- Outlines + Pydantic structured output plugs directly into graph nodes
- Status updates to Django happen as side-effects in each node
- The graph definition maps almost 1:1 to the PlantUML diagram in `agent_flow.txt`

**Trade-off:** Brings in `langchain-core` as a dependency, but can be used with direct HuggingFace/Outlines calls — no external API needed.

### 2. Custom Orchestrator with Celery Chains/Chords

Build it using what already exists:

- **Celery chains** for sequential phases (concept → culture → writing)
- **Celery chords** for parallel evaluation (cultural + concept alignment checks)
- **Custom retry logic** with a counter in the `AdaptationJob` model for the max-3-revision loops
- **State passing** via Django ORM — each phase writes its output to a related model, next phase reads it

**Pros:**
- Zero new dependencies
- Leverages existing Celery infrastructure and solo pool
- Full control over every detail
- Fits naturally with Django admin status tracking

**Cons:**
- Essentially building a state machine from scratch
- Celery's chain/chord primitives get awkward for conditional loops (the "revise up to 3 times" pattern)
- Error handling and retry logic becomes hand-rolled boilerplate
- No built-in checkpointing or graph visualization

### 3. Prefect or Temporal

Workflow orchestration engines that handle complex DAGs with retries and state:

- **Prefect** — Python-native, good for data pipeline DAGs with retries and conditional branching
- **Temporal** — More heavyweight, designed for long-running workflows with durability guarantees

**Pros:** Robust, battle-tested orchestration with built-in retry, timeout, and state management.

**Cons:** Significant infrastructure addition (separate server process), overkill for a single pipeline, and neither is designed specifically for LLM agent patterns.

## Comparison Matrix

| Requirement from Spec | LangGraph | Custom Celery | Prefect/Temporal |
|---|---|---|---|
| Supervisor → sub-agent routing | Native pattern | Manual dispatch | Possible but awkward |
| Max 3 revision loops | Conditional edges + state counter | Manual retry logic | Retry policies |
| Sequential phases with handoff | Graph nodes + edges | Celery chains | Task dependencies |
| Status updates to Django | Side-effects in nodes | Natural fit | Webhook/callback |
| Structured output (Pydantic) | Works with Outlines | Works with Outlines | Works with Outlines |
| Local model selection | Manual (reuse existing) | Manual (reuse existing) | Manual (reuse existing) |
| Model fallback on retry | Graph state + conditional | Manual | Retry policies |
| Failure/escalation handling | Graph branching | Manual | Built-in |
| Visualization of flow | Built-in graph rendering | None | Dashboard |

## Recommendation

**LangGraph** is the strongest fit. The spec's supervisor pattern with conditional evaluation loops is exactly what LangGraph was designed for. The existing Outlines + Pydantic structured output and `Language.primary_model` / `alternative_models` configuration plug in directly — no external APIs required.

### Practical Integration Sketch

```
Celery Task (create_adaptation_task)
  └── LangGraph StateGraph execution
        │
        │   Model resolution: Language.primary_model (default)
        │   Override: AdaptationJob.llm_model (if set)
        │   Fallback: Language.alternative_models (on retry)
        │
        ├── concept_node    → Outlines + resolved local model
        ├── culture_node    → Outlines + resolved local model
        ├── writer_node     → Outlines + resolved local model
        ├── eval_culture    → conditional edge (pass → next, fail → writer, max 3)
        ├── eval_concept    → conditional edge (pass → next, fail → writer, max 3)
        └── END or FAIL     → update AdaptationJob status
```

Each node writes status to Django ORM as a side-effect, and the graph state carries the accumulated briefs/scripts between nodes. The Celery task launches the graph and waits for completion — keeping the existing queue infrastructure intact. All inference runs locally via HuggingFace models managed through the existing `LLMModel` registry.
