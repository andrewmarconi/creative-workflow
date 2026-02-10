# Documentation Site Redesign — Specification

## Overview

This specification defines the recommended structure for the Generative Creative Lab GitHub Pages documentation site. The outline follows the [Diataxis framework](https://diataxis.fr/) (Tutorials / How-To Guides / Reference / Explanation), the industry standard for developer documentation.

The existing site uses Sphinx with RST + Markdown (MyST), deployed automatically to GitHub Pages via `.github/workflows/docs.yml`. This redesign preserves that toolchain while reorganizing content for better developer experience.

---

## Site Map

```
Home
Getting Started
  ├── Installation & Setup
  ├── Your First Image
  └── Your First Adaptation
Concepts
  ├── Architecture Overview
  ├── Diffusion Models
  ├── Adaptation Pipeline
  ├── Audience Targeting
  └── Observability
Guides
  ├── Image Generation
  │   ├── Adding a New Model
  │   ├── Working with LoRAs
  │   ├── Prompt Enhancement
  │   └── Compel Prompt Weighting
  ├── TV Spot Adaptation
  │   ├── Creating a Campaign
  │   ├── Origin & Adaptation Ad Units
  │   ├── Importing TV Spots (JSON)
  │   ├── Video Upload & Analysis
  │   └── Storyboard Generation
  ├── Audiences & Brands
  │   ├── Regions, Countries & Languages
  │   ├── Segments & Personas
  │   └── Brand Configuration
  ├── Pipeline Customization
  │   ├── Prompt Template Editing
  │   ├── Per-Node Model Selection
  │   └── Pipeline Settings
  └── Operations
      ├── Data Import & Export
      ├── Grafana & Log Querying
      └── Troubleshooting
Reference
  ├── Management Commands
  ├── Data Schemas (JSON)
  ├── Model Specifications
  ├── Configuration (.env & presets.json)
  ├── Celery Tasks & Queues
  └── API Reference (autodoc)
Project
  ├── Philosophy & Design Principles
  ├── Contributing
  ├── Roadmap
  ├── Research Notes
  └── Changelog
```

---

## Page-by-Page Breakdown

### Home (`index`)

Single landing page with project description, key capabilities (multi-model diffusion, multi-agent adaptation, audience targeting), and quick navigation cards to the four main sections.

---

### Getting Started (Tutorials — learning-oriented)

| Page | Content |
|---|---|
| **Installation & Setup** | Prerequisites (Python 3.12+, uv, Docker), clone, `uv sync`, `docker compose up`, migrations, `createsuperuser`, `import_presets`, verify with `honcho start`. Replaces current `quickstart.rst`. |
| **Your First Image** | Step-by-step walkthrough: create a Prompt in admin, create a DiffusionJob, watch Celery pick it up, view results. Screenshots of admin UI at each step. |
| **Your First Adaptation** | End-to-end: create a Brand, Campaign, origin VideoAdUnit with script rows, then an adaptation targeting a different market. Watch the pipeline run, view briefs and adapted script. |

These three pages form a progressive onboarding ramp — from zero to productive.

---

### Concepts (Explanation — understanding-oriented)

| Page | Content |
|---|---|
| **Architecture Overview** | Process model (4 processes), src layout, Django apps map, data flow diagrams (Mermaid). How the pieces fit together at a high level. Consolidates current `architecture.rst`. |
| **Diffusion Models** | Template Method Pattern, BaseModel → Mixins → Concrete models, ModelFactory, warm caching, device optimization (MPS/CUDA). When and why each model is suited for different tasks. |
| **Adaptation Pipeline** | LangGraph multi-agent system, the 7 nodes explained conceptually, evaluation gates and retry logic, state flow diagram, model resolution chain. |
| **Audience Targeting** | Geographic hierarchy (Region → Country → Language), non-geographic segments (Demographic / Behavioral / Psychographic), Personas as composites, insights composition and how it feeds the pipeline. |
| **Observability** | Logging architecture (5 log files → Alloy → Loki → Grafana), structured JSON logs, Flower for task monitoring, how to debug a failed job. |

---

### Guides (How-To — task-oriented)

#### Image Generation

| Page | Content |
|---|---|
| **Adding a New Model** | Concrete steps: create model file, implement `_create_pipeline()`, register in factory, add presets.json entry, `import_presets`. Code snippets for simple vs. complex models. Replaces current `adding-models.rst`. |
| **Working with LoRAs** | Add a LoRA to presets.json, theme filtering, CivitAI AIR auto-download, trigger words, strength/guidance overrides. |
| **Prompt Enhancement** | Three methods compared (rule-based / HF / Anthropic), when to use each, style options, creativity levels, how enhancement integrates with jobs. |
| **Compel Prompt Weighting** | `(word:1.3)` syntax, long prompt support, which models support it (SDXL/SD15), practical examples. |

#### TV Spot Adaptation

| Page | Content |
|---|---|
| **Creating a Campaign** | Admin walkthrough: new Campaign, linking Brand, setting original script data. |
| **Origin & Adaptation Ad Units** | Origin vs. adaptation, the `source_ad_unit` chain, script rows, status lifecycle. |
| **Importing TV Spots (JSON)** | JSON format specification, required/optional fields, `import_tvspot` command. Replaces current `importing-tvspots.rst`. |
| **Video Upload & Analysis** | Upload flow, security validation, analysis results (scene detection, transcription, object detection, visual style, audience insights). |
| **Storyboard Generation** | Creating a Storyboard, linking to DiffusionModel/LoRA, prompt generation from script rows, progress tracking. |

#### Audiences & Brands

| Page | Content |
|---|---|
| **Regions, Countries & Languages** | Data model, how to add a new market, language-model linking, M2M relationships. |
| **Segments & Personas** | Creating segments (3 categories), building personas with cascading selectors, how personas feed adaptation. |
| **Brand Configuration** | Brand voice/values/guidelines fields, how brand evaluation uses them, linking brands to campaigns. |

#### Pipeline Customization

| Page | Content |
|---|---|
| **Prompt Template Editing** | Admin walkthrough, Jinja2 syntax, versioning, variable reference, cache invalidation. |
| **Per-Node Model Selection** | Resolution chain explained with examples, overriding at AdUnit vs. PipelineSettings level. |
| **Pipeline Settings** | Singleton config, node defaults, global fallback, practical tuning advice. |

#### Operations

| Page | Content |
|---|---|
| **Data Import & Export** | All 24+ management commands organized by domain, dependency order for imports, `--dry-run` usage, backup workflows. |
| **Grafana & Log Querying** | Access at :3000, Loki query examples by job type, filtering errors, correlating task IDs across logs. |
| **Troubleshooting** | Expanded from current page: model loading, LoRA, CivitAI, Celery, pipeline failures, common Django errors. |

---

### Reference (Reference — information-oriented)

| Page | Content |
|---|---|
| **Management Commands** | Complete table of all commands with synopsis, flags, and examples. Single-page quick reference. |
| **Data Schemas (JSON)** | Field-by-field specification for all 14 data files (presets, reference data, templates, segments, brands). Consolidates current `data-schemas.rst` and `export_formats.md`. |
| **Model Specifications** | Table of all 7+ models: pipeline class, default steps, CFG, negative prompt support, architecture tag, VRAM requirements. Replaces current `model-reference.rst`. |
| **Configuration** | `.env` variables (required vs. optional), `presets.json` structure, `settings.py` key settings, Docker Compose service ports. |
| **Celery Tasks & Queues** | Task signatures, queue routing, time limits, retry behavior, result storage. |
| **API Reference** | Auto-generated from docstrings (autodoc). Organized by app: core, diffusion, tvspots, audiences, lib. Keep current structure. |

---

### Project (Meta)

| Page | Content |
|---|---|
| **Philosophy & Design Principles** | Why this project exists, creative AI principles, technical foundations. Keep current `philosophy.rst`. |
| **Contributing** | Dev setup, code style, naming conventions, PR process. Consolidate `CONTRIBUTING.md` + current `contributing.rst`. |
| **Roadmap** | Completed milestones, current priorities, future ideas, non-goals. Keep current `roadmap.rst`. |
| **Research Notes** | Multilingual model selection guide, adaptation profiles, security considerations. Consolidate current `research/` and `security/`. |
| **Changelog** | Include from `CHANGELOG.md`. Keep current approach. |

---

## Migration from Current Structure

| Current | Recommended | Rationale |
|---|---|---|
| `about/` + `user/` + `developer/` | `getting-started/` + `concepts/` + `guides/` + `reference/` | Diataxis alignment — organizes by *reader intent* not author's mental model |
| Quickstart is the only tutorial | Three progressive tutorials | Covers both core workflows (diffusion + adaptation), not just setup |
| `research/` as top-level section | Folded into `project/research-notes` | Research is supplementary, not a primary navigation target |
| `security/` as standalone section | Folded into `project/research-notes` | Single page doesn't warrant its own section |
| `export_formats.md` floating at root | Merged into `reference/data-schemas` | Eliminates orphan page, consolidates related content |
| No operations/observability docs | Dedicated guides section | Grafana/Loki/logging is a significant feature that deserves coverage |
| No video analysis documentation | Covered in TV Spot guides | Major feature currently undocumented |
| Audience/brand docs sparse | Three dedicated guide pages | Reflects the depth of the audience targeting system |

---

## Design Principles

1. **Progressive disclosure** — Home → Getting Started → Concepts → Guides → Reference. Each level adds depth.
2. **Task-oriented navigation** — Guides are named for what the reader wants to *do*, not what the code *is*.
3. **Single source of truth** — No content duplication between Concepts and Reference. Concepts explain *why*; Reference lists *what*.
4. **~30 pages total** — Manageable scope. Every page has a clear purpose and audience.
5. **Scannable reference** — Tables and command lists for quick lookup in the Reference section.

---

## File Structure

Proposed `docs/` directory layout after migration:

```
docs/
├── index.rst
├── getting-started/
│   ├── installation.rst
│   ├── first-image.rst
│   └── first-adaptation.rst
├── concepts/
│   ├── architecture.rst
│   ├── diffusion-models.rst
│   ├── adaptation-pipeline.rst
│   ├── audience-targeting.rst
│   └── observability.rst
├── guides/
│   ├── image-generation/
│   │   ├── adding-models.rst
│   │   ├── loras.rst
│   │   ├── prompt-enhancement.rst
│   │   └── compel-weighting.rst
│   ├── tv-spot-adaptation/
│   │   ├── creating-campaigns.rst
│   │   ├── ad-units.rst
│   │   ├── importing-tvspots.rst
│   │   ├── video-analysis.rst
│   │   └── storyboards.rst
│   ├── audiences-brands/
│   │   ├── regions-countries-languages.rst
│   │   ├── segments-personas.rst
│   │   └── brand-configuration.rst
│   ├── pipeline/
│   │   ├── prompt-templates.rst
│   │   ├── per-node-models.rst
│   │   └── pipeline-settings.rst
│   └── operations/
│       ├── data-import-export.rst
│       ├── grafana-logging.rst
│       └── troubleshooting.rst
├── reference/
│   ├── management-commands.rst
│   ├── data-schemas.rst
│   ├── model-specifications.rst
│   ├── configuration.rst
│   ├── celery-tasks.rst
│   └── api/
│       ├── index.rst
│       ├── core.rst
│       ├── diffusion.rst
│       ├── tvspots.rst
│       ├── audiences.rst
│       └── lib.rst
├── project/
│   ├── philosophy.rst
│   ├── contributing.rst
│   ├── roadmap.rst
│   ├── research-notes.rst
│   └── changelog.rst
├── _static/
│   └── custom.css
├── _templates/
├── conf.py
└── Makefile
```
