# TV Spot Adaptations Feature

## Quick Start for Implementation

Read these documents in order:

1. **[feature_adaptation.md](feature_adaptation.md)** - User stories, acceptance criteria, implementation order
2. **[schemas.md](schemas.md)** - Django models and relationships
3. **[json_import_format.md](json_import_format.md)** - JSON schema for importing TV spots
4. **[adaptation_prompt_for_llm.md](adaptation_prompt_for_llm.md)** - LLM prompt template for creating adaptations
5. **[adaptation_rules.md](adaptation_rules.md)** - Market-specific cultural/regulatory rules (seed data)
6. **[logging_requirements.md](logging_requirements.md)** - Structured logging requirements for Loki/Grafana

## Feature Summary

| Story | Description | Key Components |
|-------|-------------|----------------|
| 1 | Import TV Spot from JSON | Management command, admin action, validation |
| 2 | Create Market Adaptation | LLM (Qwen 3 8B + Outlines), Celery task |
| 3 | Generate Storyboard | LLM prompt generation, DiffusionJob creation |
| 4 | Batch Generate Storyboards | Iterate over all adaptations |
| 5 | View Storyboard | Unfold admin template, 3-column grid |

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM for adaptation | Qwen 3 8B (Q4_K_M) | Multilingual, local, sufficient for structured output |
| Structured output | Outlines library | Guarantees valid JSON, lighter than vLLM |
| Celery queue for LLM | `enhancement` | Reuse existing queue, simplify config |
| Celery queue for images | `default` | Existing GPU queue |
| Market rules storage | Markdown TextField | LLM-native format, easy to edit |
| Storyboard viewer | Unfold admin template | Stays within admin, uses existing Tailwind |

## Models Overview

```
TvSpot
  └── TvSpotVersion (origin + N adaptations)
        ├── TvSpotScriptRow (script content)
        └── StoryboardJob (generation config)
              └── StoryboardImage → DiffusionJob

AdaptationMarket (market rules)
```

## Implementation Phases

1. **Phase 1**: Models, migrations, market seed data
2. **Phase 2**: JSON import (command + admin)
3. **Phase 3**: LLM adaptation with Outlines
4. **Phase 4**: Storyboard generation
5. **Phase 5**: Storyboard viewer

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    "outlines>=0.1.0",
]
```

## Commands to Create

```bash
uv run manage.py import_markets      # Seed AdaptationMarket from rules
uv run manage.py import_tvspot       # Import TV spot from JSON
```
