---
name: update-docs
description: Update all project documentation to match the current state of the codebase
user-invocable: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(cd docs && make html:*), Bash(cd docs && make clean:*), Bash(ls:*), Bash(python:*), Bash(uv run python:*)
---

# Update Documentation Skill

Comprehensively update all project documentation so it accurately reflects the current state of the codebase. This covers the roadmap, user documentation, developer documentation, and API reference.

## Overview

The documentation lives under `docs/` and is built with Sphinx (RTD theme). Run through each documentation section below, compare it against the actual code, and make the docs match reality. Do NOT invent features that don't exist — only document what the code actually does.

## Pre-Flight

Before making changes:

1. Read `CLAUDE.md` for the latest architecture notes and project structure
2. Scan `src/cw/` to understand the current app layout and module inventory
3. Run `cd docs && make clean && make html` to confirm the docs build cleanly before you start

## Sections to Update

Work through each section in order. For every section, read the corresponding source files, compare against the docs, and update the docs to match.

### 1. Roadmap (`docs/about/roadmap.rst`)

**Source of truth**: GitHub Issues (use `gh issue list`), recent git log, and `CLAUDE.md`

- Update **Development Status** prose to reflect current project state
- Update **Feature & Experiment Ideas** — add new ideas from issues, mark completed ones
- Check that GitHub issue links are still valid
- Keep the tone consistent: this is a lab/framework, not a product

### 2. User Documentation

#### 2a. Quick Start (`docs/user/quickstart.rst`)

**Source of truth**: `Procfile`, `start.sh`, `docker-compose.yml`, `CLAUDE.md` Commands section

- Verify prerequisites are accurate (Python version, Docker, GPU requirements)
- Verify installation steps match actual commands (`uv sync`, `start.sh`, etc.)
- Verify the process table matches the current `Procfile` entries
- Verify database init commands are current (`migrate`, `createsuperuser`, `import_presets`, reference data)
- Verify "Creating Your First Image" steps match current admin workflow

#### 2b. User Guides (`docs/user/guides/*.rst`)

**Source of truth**: `src/cw/lib/models/`, `data/presets.json`, `src/cw/tvspots/`

- **model-reference.rst**: Verify model table matches `data/presets.json` entries and `CLAUDE.md` model notes. Check that creative characteristics descriptions are accurate for each model.
- **adding-models.rst**: Verify the step-by-step guide matches the current `BaseModel` API, mixin pattern, and `ModelFactory` registration. Confirm code examples compile against the actual base class.
- **importing-tvspots.rst**: Verify import format matches `import_adaptations` management command and current model structure (Campaign, VideoAdUnit, AdUnitScriptRow, etc.)
- Check if any new guides are needed for features that exist but aren't documented

#### 2c. Troubleshooting (`docs/user/troubleshooting.rst`)

**Source of truth**: `src/cw/settings.py`, `Procfile`, common error patterns

- Verify all referenced paths, commands, and config values are current
- Check that queue names match the current Celery configuration
- Verify Docker Compose service names and ports are current

### 3. Developer Documentation

#### 3a. Architecture (`docs/developer/architecture.rst`)

**Source of truth**: `src/cw/`, all `models.py` files, `tasks.py` files, `Procfile`

This is the most complex document. Check each section:

- **System Overview**: Verify the Mermaid diagram matches current components
- **Process Model**: Verify processes match `Procfile` (worker names, queue names, ports)
- **Queue Structure**: Verify queue names and task assignments are current
- **Data Flow — Image Generation Pipeline**: Verify steps match `src/cw/diffusion/tasks.py`
- **Model Loading and Caching**: Verify code snippet matches actual `tasks.py` cache logic
- **LoRA Loading Flow**: Verify diagram matches `src/cw/lib/civitai.py` and task flow
- **Model Architecture**: Verify class hierarchy diagram includes all current model classes. Read `src/cw/lib/models/*.py` to get the actual list.
- **Mixins**: Verify all current mixins are listed
- **Configuration Flags**: Verify flag table matches actual `BaseModel` flags
- **Database Schema — Diffusion App**: Compare ER diagram and field tables against `src/cw/diffusion/models.py`. Every field on the model should appear in the docs.
- **Database Schema — TV Spots App**: Compare ER diagram and field tables against `src/cw/tvspots/models.py`. This has been significantly refactored — models may have changed from the original TvSpot/TvSpotVersion/AdaptationMarket structure to the Campaign/AdUnit/VideoAdUnit/Storyboard structure documented in `CLAUDE.md`.
- **Cross-App References**: Verify FK references between apps are documented
- **Observability**: Verify log file names and Grafana/Loki details are current

#### 3b. Data Schemas (`docs/developer/data-schemas.rst`)

**Source of truth**: `data/*.json`, `data/*.schema.json`

- **Presets Schema**: Verify properties tables match actual `presets.json` structure
- **TV Spot Schema**: Verify against actual import format and `data/example_tvspot.json`
- **Market Profiles Schema**: Check if this data model still exists or has been replaced by the reference data system (regions, countries, languages). Update accordingly.
- Check if new schemas need documenting (e.g., reference data files: `regions.json`, `countries.json`, `languages.json`, `llm_models.json`)
- Verify all `:download:` links point to files that actually exist

#### 3c. API Reference (`docs/developer/api/`)

**Source of truth**: `src/cw/` module structure

- **index.rst**: Verify toctree lists all current API doc files
- **lib.rst**: Verify all `src/cw/lib/` modules are included. Check for new modules like `pipeline/`, `insights.py`, `preloader.py`, `prompts/` that may need `automodule` entries.
- **core.rst**: Verify against `src/cw/core/` structure
- **diffusion.rst**: Verify against `src/cw/diffusion/` structure
- **tvspots.rst**: Verify against `src/cw/tvspots/` structure. Update module descriptions to match current model names.

### 4. Supporting Files

#### 4a. Main Index (`docs/index.rst`)

- Verify toctree entries match actual files
- Verify the project description and Key Capabilities reflect current functionality

#### 4b. Philosophy (`docs/about/philosophy.rst`)

- Light touch — only update if capabilities listed don't match reality

#### 4c. Research (`docs/research/`)

- Verify research docs are still relevant and links work
- No need to update content unless referenced models/approaches have changed

## Post-Flight

After making all changes:

1. Run `cd docs && make clean && make html` and fix any build errors or warnings
2. Verify no broken cross-references (`:doc:`, `:download:` links)
3. Summarize all changes made in a clear report

## Output Format

Report your changes:

```
## Documentation Update Summary

### Roadmap
- [UPDATED/NO CHANGE] roadmap.rst: <what changed>

### User Documentation
- [UPDATED/NO CHANGE] quickstart.rst: <what changed>
- [UPDATED/NO CHANGE] model-reference.rst: <what changed>
- [UPDATED/NO CHANGE] adding-models.rst: <what changed>
- [UPDATED/NO CHANGE] importing-tvspots.rst: <what changed>
- [UPDATED/NO CHANGE] troubleshooting.rst: <what changed>

### Developer Documentation
- [UPDATED/NO CHANGE] architecture.rst: <what changed>
- [UPDATED/NO CHANGE] data-schemas.rst: <what changed>
- [UPDATED/NO CHANGE] api/lib.rst: <what changed>
- [UPDATED/NO CHANGE] api/core.rst: <what changed>
- [UPDATED/NO CHANGE] api/diffusion.rst: <what changed>
- [UPDATED/NO CHANGE] api/tvspots.rst: <what changed>

### Build Status
- [PASS/FAIL] Sphinx build: <details>
```

## Important Guidelines

- Only document what actually exists in the code — never invent features
- Preserve the existing documentation style and tone
- Keep Mermaid diagrams accurate but don't over-complicate them
- Use `:doc:` cross-references between documentation pages
- Use `automodule` directives for API docs (Sphinx autodoc handles the rest)
- If a section is already accurate, leave it alone — don't make gratuitous changes
- For the TV Spots app, pay special attention to the model refactoring — the domain model may have changed significantly from TvSpot/TvSpotVersion to Campaign/VideoAdUnit
