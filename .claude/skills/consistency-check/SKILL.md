---
name: consistency-check
description: Verify consistency between code, data, migrations, and documentation before commits
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash(python:*), Bash(uv run python:*)
---

# Consistency Check Skill

Run comprehensive consistency checks on the codebase to ensure alignment between models, migrations, admin configuration, documentation, and data files.

## What to Check

### 1. Django Models vs Migrations

Compare model definitions against migrations:

**diffusion app** (`src/cw/diffusion/`):
- `DiffusionModel` - label, slug, base_architecture, path, pipeline, settings fields
- `LoraModel` - label, path, air, base_architecture, prompt_suffix, settings fields
- `Prompt` - source_prompt, enhanced_prompt, negative_prompt, enhancement fields
- `DiffusionJob` - FK references, status, parameters, results

**tvspots app** (`src/cw/tvspots/`):
- `AdaptationMarket` - name, code, language, rules (JSONField)
- `TvSpot` - client_name, brand_name, script_title, job_id
- `TvSpotVersion` - version_type, market FK, code, language
- `TvSpotScriptRow` - order_index, shot_number, timecode, visual_text, audio_text
- `AdaptationJob` - status, FK references (tv_spot, origin_version, target_market, result_version)
- `StoryboardJob` - diffusion_model FK, lora_model FK, status
- `StoryboardImage` - FKs to storyboard_job, script_row, diffusion_job

For each model, check that the latest migration includes all fields defined in the model.

### 2. Admin Configuration vs Models

Check `src/cw/diffusion/admin.py` and `src/cw/tvspots/admin.py`:
- Verify `list_display` fields exist on the model
- Verify `search_fields` reference valid fields
- Verify `list_filter` uses valid fields or callables
- Verify `fieldsets` reference actual model fields
- Check inline admin classes reference valid related models

### 3. Documentation vs Models

Compare `docs/reference/database-schema.rst` with actual models:
- All models should be mentioned in the ER diagram
- All models should have a description section
- Cross-app references should be documented
- Cascade behavior table should match actual `on_delete` settings

### 4. Data Files Validity

Check `data/presets.json`:
- Valid JSON syntax
- All model entries have required fields: slug, label, path, pipeline, base_architecture, settings
- All lora entries have required fields: label, base_architecture
- `base_architecture` values match `BASE_ARCHITECTURE_CHOICES` in models.py

Check `data/core_data.json`:
- Valid JSON syntax
- LLM models have required fields: model_id, name
- Languages have required fields: code, name, primary_model
- Language primary_model references a valid model_id

### 5. CLAUDE.md vs Implementation

Verify `CLAUDE.md` accurately describes:
- Model-specific notes table matches actual model implementations
- Architecture choices match `BASE_ARCHITECTURE_CHOICES`
- Pipeline class names match implementations in `src/cw/lib/models/`

## Output Format

Report findings using this structure:

```
## Consistency Check Results

### Models vs Migrations
- [PASS/WARN/FAIL] diffusion app: <details>
- [PASS/WARN/FAIL] tvspots app: <details>

### Admin vs Models
- [PASS/WARN/FAIL] diffusion admin: <details>
- [PASS/WARN/FAIL] tvspots admin: <details>

### Documentation
- [PASS/WARN/FAIL] database-schema.rst: <details>

### Data Files
- [PASS/WARN/FAIL] presets.json: <details>
- [PASS/WARN/FAIL] core_data.json: <details>

### Summary
X checks passed, Y warnings, Z failures
```

## Instructions

1. Read all relevant files before making comparisons
2. Be specific about what's missing or inconsistent
3. Suggest fixes for any issues found
4. Don't modify any files - this is read-only validation
5. Run the Python consistency checker script if available: `.claude/hooks/consistency_checker.py`
