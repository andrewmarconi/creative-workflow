# Feature: TV Spot Adaptations

## Overview

This feature enables importing TV spot scripts, creating culturally-adapted versions via LLM, and generating storyboard images for visualization.

## User Stories

### Story 1: Import TV Spot from JSON

**As a** user
**I want to** import a TV spot from a JSON file
**So that** I can create adaptations and storyboards for it

#### Acceptance Criteria

1. User can import via:
   - **Management command**: `uv run manage.py import_tvspot <file.json>`
   - **Admin action**: Paste JSON in a textarea form (similar to CivitAI import)

2. System validates JSON against the expected schema (see [json_import_format.md](json_import_format.md))

3. On successful import:
   - Creates `TvSpot` with metadata
   - Creates `TvSpotVersion` with `version_type='origin'`
   - Creates `TvSpotScriptRow` for each row in the script

4. Validation errors display clear messages indicating which fields failed

#### Implementation Notes

- Management command: `cw/diffusion/management/commands/import_tvspot.py`
- Admin view: Custom URL on `TvSpotAdmin` via `get_urls()`, renders `TemplateResponse`
- Follow existing pattern from `import_from_civitai_view` in [admin.py](../../cw/diffusion/admin.py)

---

### Story 2: Create Market Adaptation

**As a** user
**I want to** create a culturally-adapted version of a TV spot
**So that** the content resonates with a specific market

#### Acceptance Criteria

1. User clicks "Create Adaptation" button on `TvSpot` detail page
2. User selects target market from `AdaptationMarket` dropdown
3. System queues an LLM task that:
   - Loads the origin version's script rows
   - Loads the target market's rules (markdown)
   - Generates adapted content using the LLM prompt template
   - Creates new `TvSpotVersion` with `version_type='adaptation'`
   - Creates adapted `TvSpotScriptRow` entries
   - Generates `visual_style_prompt` for storyboard consistency

4. User sees status indicator while adaptation is processing
5. On completion, user can view the adapted version

#### Implementation Notes

**LLM Configuration:**
- Model: Qwen 3 8B (Q4_K_M quantization)
- Library: Outlines for guided JSON output
- Context length: 8K-16K tokens
- Task queue: `enhancement` (reuse existing LLM queue)

**Celery Task:** `create_adaptation_task(tv_spot_id, market_id)`

```python
# Pseudocode for adaptation task
def create_adaptation_task(tv_spot_id: int, market_id: int):
    tv_spot = TvSpot.objects.get(id=tv_spot_id)
    market = AdaptationMarket.objects.get(id=market_id)
    origin = tv_spot.origin_version

    # Build prompt with origin script + market rules
    prompt = build_adaptation_prompt(
        origin_script=serialize_version_to_json(origin),
        market_rules=market.rules,
        market_name=market.name,
    )

    # Generate adapted JSON via Outlines
    adapted_json = generate_with_outlines(
        prompt=prompt,
        schema=TvSpotVersionSchema,
    )

    # Create version and rows from JSON
    version = create_version_from_json(tv_spot, market, adapted_json)
    return version.id
```

**Prompt Template:** See [adaptation_prompt_for_llm.md](adaptation_prompt_for_llm.md)

---

### Story 3: Generate Storyboard for Adaptation

**As a** user
**I want to** generate storyboard images for an adaptation
**So that** I can visualize the adapted spot

#### Acceptance Criteria

1. User clicks "Generate Storyboard" on `TvSpotVersion` detail page
2. User fills form with:
   - Diffusion model (required, dropdown)
   - LoRA (optional, filtered by model compatibility)
   - Images per row (number input, default: 1)
3. System creates:
   - One `StoryboardJob` linking to the version
   - One `Prompt` per script row (LLM-generated from visual_text + audio_text)
   - One `DiffusionJob` per (row × images_per_row)
   - `StoryboardImage` entries linking jobs to rows
4. Jobs are queued to the `default` (GPU) queue
5. `DiffusionJob.identifier` follows pattern: `{job_id}_{version_code}_row-{NN}_img-{NN}`

#### Implementation Notes

**Prompt Generation:**

The LLM generates image prompts from each script row, prefixed with the version's `visual_style_prompt`:

```python
def generate_image_prompt(version: TvSpotVersion, row: TvSpotScriptRow, model: DiffusionModel) -> str:
    system_prompt = f"""Create a rich image generation prompt optimized for {model.label}.

The prompt should visualize this scene from a TV commercial:

VISUAL: {row.visual_text}
AUDIO: {row.audio_text}

Requirements:
- Focus on the visual elements described
- Use descriptive language suitable for image generation
- Maintain consistency with the overall style
- Output ONLY the prompt text, no explanations
"""

    # Generate via LLM
    image_prompt = generate_with_llm(system_prompt)

    # Prepend visual style baseline
    if version.visual_style_prompt:
        return f"{version.visual_style_prompt}, {image_prompt}"
    return image_prompt
```

**Visual Style Generation:**

During adaptation (Story 2), the LLM also generates a `visual_style_prompt` based on the adapted script content:

```python
style_prompt = """Based on this adapted TV spot script, generate a concise visual style
description (50-100 words) that should be prepended to all image generation prompts
to ensure visual consistency. Include: color palette, mood, lighting style,
camera perspective, and any recurring visual motifs.

Script: {adapted_script_json}

Output ONLY the style description, no explanations."""
```

**Celery Task:** `generate_storyboard_task(storyboard_job_id)`

---

### Story 4: Batch Generate Storyboards

**As a** user
**I want to** generate storyboards for all adaptations of a TV spot
**So that** I can visualize all market versions at once

#### Acceptance Criteria

1. User clicks "Generate All Storyboards" on `TvSpot` detail page
2. User fills form with model/LoRA/images_per_row (same as Story 3)
3. System creates a `StoryboardJob` for each adaptation version
4. All jobs are queued to the `default` queue

#### Implementation Notes

- Reuses `generate_storyboard_task` from Story 3
- Admin action iterates over `tv_spot.versions.filter(version_type='adaptation')`

---

### Story 5: View Storyboard

**As a** user
**I want to** view the generated storyboard
**So that** I can review the visual representation of the spot

#### Acceptance Criteria

1. "View Storyboard" button appears on `TvSpotVersion` detail page (enabled when images exist)
2. Clicking opens a storyboard view page within Django admin (Unfold-styled)
3. Page displays:
   - **Header**: TvSpot metadata (client, brand, title, TRT) + version info (market, language)
   - **Grid**: 3-column layout of storyboard images
   - **Per image**: Image thumbnail + script row text (visual_text, audio_text) below

#### Implementation Notes

**Template:** `templates/admin/diffusion/tvspotversion/storyboard_view.html`

```html
{% extends "admin/base_site.html" %}
{% load static %}

{% block content %}
<div class="p-6">
    <!-- Header -->
    <div class="mb-8">
        <h1 class="text-2xl font-bold">{{ version.tv_spot.script_title }}</h1>
        <p class="text-gray-600">
            {{ version.tv_spot.client_name }} | {{ version.name }} | {{ version.language }}
        </p>
    </div>

    <!-- Storyboard Grid -->
    <div class="grid grid-cols-3 gap-6">
        {% for image in images %}
        <div class="border rounded-lg overflow-hidden">
            <a href="{{ image.diffusion_job.result_images.0 }}" target="_blank">
                <img src="{{ image.diffusion_job.result_images.0 }}" class="w-full h-48 object-cover">
            </a>
            <div class="p-4 text-sm">
                <p class="font-medium">{{ image.script_row.shot_number|default:image.script_row.order_index }}</p>
                <p class="text-gray-700 mt-1"><strong>Visual:</strong> {{ image.script_row.visual_text|truncatewords:30 }}</p>
                <p class="text-gray-500 mt-1"><strong>Audio:</strong> {{ image.script_row.audio_text|truncatewords:30 }}</p>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

**Admin URL:** Add via `TvSpotVersionAdmin.get_urls()`:

```python
path(
    '<int:version_id>/storyboard/',
    self.admin_site.admin_view(self.storyboard_view),
    name='tvspotversion_storyboard',
)
```

---

## Technical Architecture

### New Files

| File | Purpose |
|------|---------|
| `cw/diffusion/models.py` | Add new models (or new file `cw/adaptations/models.py`) |
| `cw/diffusion/management/commands/import_tvspot.py` | Import command |
| `cw/diffusion/management/commands/import_markets.py` | Seed markets from adaptation_rules.md |
| `lib/adaptation.py` | LLM adaptation logic with Outlines |
| `templates/admin/diffusion/tvspot/import_tvspot.html` | Import form template |
| `templates/admin/diffusion/tvspotversion/storyboard_view.html` | Storyboard viewer |
| `templates/admin/diffusion/tvspotversion/generate_storyboard.html` | Generation form |

### Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing
    "outlines>=0.1.0",  # Structured LLM output
]
```

### Celery Tasks

| Task | Queue | Purpose |
|------|-------|---------|
| `create_adaptation_task` | `enhancement` | Generate adapted version via LLM |
| `generate_storyboard_task` | `enhancement` | Generate image prompts via LLM, then queue DiffusionJobs |
| `generate_images_task` | `default` | Existing image generation task |

### Data Seeding

**Markets:** Create `data/adaptation_markets.json` with the 5 markets from `adaptation_rules.md`:

```json
[
    {"name": "US Hispanic", "code": "us-hispanic", "rules": "...markdown..."},
    {"name": "French & Benelux", "code": "fr-benelux", "rules": "...markdown..."},
    {"name": "Turkish", "code": "tr", "rules": "...markdown..."},
    {"name": "Japanese", "code": "jp", "rules": "...markdown..."},
    {"name": "South Korean", "code": "kr", "rules": "...markdown..."}
]
```

Import via: `uv run manage.py import_markets`

---

## Implementation Order

1. **Phase 1: Models & Data**
   - [ ] Create models in `models.py`
   - [ ] Create migrations
   - [ ] Create `import_markets` command
   - [ ] Seed markets from `adaptation_rules.md`

2. **Phase 2: Import (Story 1)**
   - [ ] Define JSON import schema
   - [ ] Create `import_tvspot` command
   - [ ] Create admin import action/view
   - [ ] Add basic admin for TvSpot, TvSpotVersion, TvSpotScriptRow

3. **Phase 3: Adaptation (Story 2)**
   - [ ] Add Outlines dependency
   - [ ] Implement `lib/adaptation.py` with LLM integration
   - [ ] Create `create_adaptation_task`
   - [ ] Add "Create Adaptation" admin action

4. **Phase 4: Storyboard Generation (Stories 3 & 4)**
   - [ ] Implement prompt generation logic
   - [ ] Create `generate_storyboard_task`
   - [ ] Add "Generate Storyboard" admin form
   - [ ] Add "Generate All Storyboards" admin action

5. **Phase 5: Storyboard Viewer (Story 5)**
   - [ ] Create storyboard view template
   - [ ] Add admin URL and view
   - [ ] Add conditional "View Storyboard" button
