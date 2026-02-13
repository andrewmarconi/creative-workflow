# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Generative Creative Lab is a Django + Celery application for multi-model diffusion image generation. It uses Django Unfold for the admin UI, PostgreSQL for storage, and Valkey/Redis as the Celery broker. Models supported: Z-Image Turbo, Flux.1-dev, Flux.2 Klein, Qwen-Image-2512, SDXL Turbo, DreamShaper XL Lightning, Juggernaut XL v9, Realistic Vision v5.1.

## Commands

### Setup & Run
```bash
uv sync                                 # Install/sync dependencies
./start.sh                              # Start all processes (recommended, waits for containers)
uv run honcho start                     # Start all processes (parallel, no dependency ordering)
uv run honcho start docker django       # Start subset of processes (without workers)
```

### Individual Processes (from Procfile)
```bash
docker compose up                               # PostgreSQL 17 + Valkey
uv run manage.py runserver                      # Django dev server on :8000
uv run celery -A cw worker -Q default   # Single worker (handles all tasks sequentially)
uv run celery -A cw flower --port=5555          # Flower task monitor on :5555
```

### Database & Django
```bash
uv run manage.py migrate                        # Run migrations
uv run manage.py import_presets                 # Sync data/presets.json → database
uv run manage.py export_presets                 # Export models/LoRAs from database to JSON
uv run manage.py import_prompts                 # Bulk import prompts
uv run manage.py export_prompts                 # Export prompts to file
uv run manage.py import_adaptations             # Import adaptations.json into prompts/jobs
uv run manage.py preload_models                 # Pre-download models to HF cache
uv run manage.py createsuperuser                # Create admin user

# Prompt Templates (LLM prompts)
uv run manage.py import_prompt_templates        # Import from data/prompt_templates.json to database
uv run manage.py import_prompt_templates --dry-run  # Preview import without changes
uv run manage.py export_prompt_templates        # Export active templates to data/prompt_templates.json
uv run manage.py export_prompt_templates --dir custom/  # Export to custom directory

# Reference Data (Regions, Countries, Languages, LLM Models)
uv run manage.py generate_reference_data        # Generate countries/languages from Babel CLDR to data/
uv run manage.py generate_reference_data --dry-run    # Preview without writing files
uv run manage.py generate_reference_data --min-population 10  # Higher language inclusion threshold
uv run manage.py export_reference_data          # Export to separate files in data/
uv run manage.py export_reference_data --dir custom/  # Export to custom directory
uv run manage.py import_reference_data          # Import from data/ directory
uv run manage.py import_reference_data --dry-run      # Preview without importing

# Audience Data (Segments, Personas)
uv run manage.py export_segments                # Export segments to data/segments.json
uv run manage.py export_segments --dir custom/  # Export to custom directory
uv run manage.py import_segments                # Import segments from data/segments.json
uv run manage.py import_segments --dry-run      # Preview without importing
uv run manage.py export_personas                # Export personas to data/personas.json + persona_segments.json
uv run manage.py export_personas --dir custom/  # Export to custom directory
uv run manage.py import_personas                # Import personas from data/personas.json
uv run manage.py import_personas --dry-run      # Preview without importing

# Brand Data
uv run manage.py export_brands                  # Export brands to data/brands.json
uv run manage.py export_brands --dir custom/    # Export to custom directory
uv run manage.py import_brands                  # Import brands from data/brands.json
uv run manage.py import_brands --dry-run        # Preview without importing
```

### Testing
```bash
uv run python test_admin.py                     # Run admin tests
uv run manage.py test cw.diffusion.tests -v2    # Diffusion app tests (ControlNet, models)
uv run manage.py test cw.tvspots.tests -v2      # TV spots tests (requires PostgreSQL)
```

### Documentation
```bash
cd docs && make html                            # Build HTML documentation
open docs/_build/html/index.html                # View documentation
cd docs && make clean                           # Clean build artifacts
```

### World Values Survey
```bash
uv run manage.py import_wvs                     # Download & import WVS cultural profiles into Country insights
uv run manage.py import_wvs --dry-run            # Preview without importing
uv run manage.py import_wvs --force-download      # Force re-download from Kaggle
```

### Observability & Logging
```bash
# View logs locally (JSON format)
tail -f logs/tasks.log                          # Task execution logs (all workers)
tail -f logs/worker_default.log                 # Image generation worker only
tail -f logs/worker_enhancement.log             # Prompt enhancement worker only
tail -f logs/django.log                         # Django server logs
tail -f logs/celery.log                         # Celery general logs

# Parse JSON logs with jq
cat logs/tasks.log | jq 'select(.levelname == "ERROR")'

# Grafana Loki - Log aggregation & search
# 1. Start docker-compose (includes Loki, Alloy, Grafana)
# 2. Logs are automatically collected from logs/*.log
# 3. Access Grafana UI at http://localhost:3000
# 4. Navigate to Explore → select Loki data source
# 5. Query examples:
#    - {job="django"} - All Django logs
#    - {job="celery"} | json | level="ERROR" - Celery errors
#    - {job="tasks"} |= "image generation" - Search for text
```

## Architecture

### Process Model
Four processes run concurrently (defined in `Procfile`, launched via `uv run honcho start`):
1. **docker** — PostgreSQL 17 (port 5435) + Valkey (port 6379) + Grafana/Loki (log aggregation)
2. **django** — Django dev server (port 8000)
3. **worker** — Single Celery worker on `default` queue (all tasks: prompt enhancement, image generation)
4. **flower** — Celery task monitor (port 5555) — real-time view of active, queued, and completed tasks

Celery uses `solo` pool (single-threaded) to prevent concurrent model loading. This ensures efficient GPU memory usage:
- Storyboard generation: All prompts enhanced sequentially → then all images generated sequentially
- Prevents loading multiple models simultaneously (Qwen + diffusion model)
- Natural task batching with single queue

**Grafana + Loki** (via `docker-compose.yml`, always enabled):
- **Loki** (port 3100) — Log aggregation backend, stores all logs
- **Alloy** — Unified observability collector, ships logs from `logs/*.log` to Loki
- **Grafana** (port 3000) — Web UI for searching and viewing logs

Access Grafana UI at http://localhost:3000 (anonymous login enabled for local dev).

### Project Structure

Uses **src layout** for proper Python packaging:
```
generative-creative-lab/
├── src/cw/              # Main package (Django project + apps + lib)
│   ├── diffusion/       # Django app for image generation
│   │   └── templates/   # App-specific admin templates
│   ├── tvspots/         # Django app for TV spot management
│   │   └── templates/   # App-specific admin templates
│   └── lib/             # Supporting library modules
│       ├── models/      # Diffusion model implementations
│       ├── loras/       # LoRA management
│       └── *.py         # Utilities (civitai, prompt_enhancer, etc.)
├── manage.py            # Django management script
├── staticfiles/         # collectstatic output (not source files)
├── media/               # User-uploaded content
├── data/                # Configuration files (presets.json)
└── logs/                # Application logs
```

### Model Architecture (Refactored 2026-02)

**Template Method Pattern** - Eliminates 70%+ code duplication:

**BaseModel** (`src/cw/lib/models/base.py`) - Abstract base with concrete template methods:
- `load_pipeline()` - Concrete template (calls `_create_pipeline()` hook)
- `generate()` - Concrete template (calls `_build_prompts()`, `_build_pipeline_kwargs()`, etc.)
- Common functionality: device setup, LoRA management, cache clearing, metadata building
- Configuration-driven behavior via flags: `force_default_guidance`, `enable_debug_logging`, etc.

**Mixins** (`src/cw/lib/models/mixins.py`) - Shared behaviors via multiple inheritance:
- `CompelPromptMixin` - Long prompt handling (>77 tokens) and prompt weighting for CLIP-based models using Compel library
- `CLIPTokenLimitMixin` - (Legacy) 77-token truncation for SDXL/SD15 models (replaced by CompelPromptMixin)
- `DebugLoggingMixin` - Debug print statements (enabled via config)

**Concrete Models** - Minimal implementations (20-70 lines each):
- Only override `_create_pipeline()` (abstract, required)
- Optionally override hooks for model-specific behavior:
  - `_build_prompts()` - Custom prompt handling (token limiting, debug logging)
  - `_build_pipeline_kwargs()` - Model-specific parameters (callbacks, runtime detection)
  - `_apply_device_optimizations()` - Custom device optimizations
  - `_handle_special_prompt_requirements()` - Special prompt needs (Qwen)
- Everything else inherited from BaseModel and mixins

**Configuration Flags** (in `data/presets.json` settings):
- `force_default_guidance` - Force default guidance_scale (ignores parameter, Turbo models)
- `enable_debug_logging` - Enable debug print statements via DebugLoggingMixin
- `use_sequential_cpu_offload` - Use sequential vs model CPU offload (CUDA)
- `max_sequence_length` - Context length for Flux variants
- `load_in_8bit` - 8-bit quantization for Qwen

**Model Implementations**: ZImageTurboModel, FluxModel, Flux2KleinModel, QwenImageModel, SDXLModel, SDXLTurboModel, SD15Model, SDXLControlNetModel, SD15ControlNetModel

**Factory**: `ModelFactory.create_model()` in `src/cw/lib/models/__init__.py` dispatches by pipeline type

### Key Code Paths

**Django app** — `src/cw/diffusion/`:
- `models.py` — ORM models: `DiffusionModel`, `LoraModel` (with theme field for categorization), `ControlNetModel`, `Prompt`, `DiffusionJob` (with optional ControlNet fields: `controlnet_model`, `reference_image`, `preprocessing_type`, `conditioning_scale`, `control_guidance_end`)
- `admin.py` — Django Unfold admin (primary UI for creating prompts, queuing jobs, viewing results)
- `tasks.py` — Celery tasks: `generate_images_task(job_id)`, `enhance_prompt_task(prompt_id)`

**Django app** — `src/cw/tvspots/`:
- `models.py` — TV spot campaign and ad unit models:
  - `Brand` — Brand reference data with voice, values, visual identity guidelines, and insights
  - `Campaign` — Top-level campaign container with job_id, client/brand info, FK to Brand, and original script data
  - `AdUnit` — Polymorphic base class for all ad unit types (VIDEO, AUDIO, PRINT) with multi-agent pipeline support, optional Brand override, and per-node model config (pipeline_model_config JSONField)
  - `VideoAdUnit` — Video-specific ad unit (merges origin creation + adaptation pipeline + script content)
  - `AdUnitScriptRow` — Script rows (shot/visual/audio) linked to any AdUnit
  - `Storyboard` — Storyboard generation job linking VideoAdUnit to DiffusionModel. Supports `source_type`: `"text"` (from script rows) or `"keyframe"` (ControlNet wireframe from video keyframes). Keyframe mode adds `controlnet_model`, `preprocessing_type`, `conditioning_scale`, `control_guidance_end`, `style_prompt` fields.
  - `StoryboardImage` — Individual storyboard frames linking script rows to DiffusionJobs (optional `key_frame` FK for wireframe mode)
- `admin.py` — Django Unfold admin for campaign management, ad unit creation, and storyboard generation
- `tasks.py` — Celery tasks: `create_adaptation_task(video_ad_unit_id)`, `generate_storyboard_task(storyboard_id)`, `generate_wireframe_storyboard_task(storyboard_id)`

**Domain Model Architecture** (Refactored 2026-02):
```
Brand (reference data: voice, values, guidelines)
Campaign (job container, FK to Brand)
  ├── VideoAdUnit (origin, no source_ad_unit)
  │     ├── AdUnitScriptRow (visual/audio script content)
  │     └── Storyboard → StoryboardImage → DiffusionJob
  └── VideoAdUnit (adaptation, references source_ad_unit, optional Brand override)
        ├── Region/Country/Language (target localization)
        ├── AdUnitScriptRow (culturally-adapted script)
        ├── concept_brief, cultural_brief (pipeline output)
        ├── evaluation_history (pipeline validation results)
        └── pipeline_model_config (per-node LLM overrides)
PipelineSettings (singleton: per-node default models + global default)
```

**Key Model Features**:
- **Polymorphic AdUnit**: Multi-table inheritance allows extensibility (AudioAdUnit, PrintAdUnit in future)
- **Adaptation Chain**: `source_ad_unit` FK creates origin → adaptation graph within same Campaign
- **Pipeline Integration**: VideoAdUnit includes pipeline status tracking, JSON brief storage, metadata, and per-node model config
- **Multi-Agent Pipeline**: Powered by LangGraph with concept extraction, cultural research, writing, and evaluation agents (format, cultural, concept, brand)
- **Per-Node Model Selection**: Each pipeline node can use a different LLM model. Resolution chain: AdUnit override → PipelineSettings node default → PipelineSettings global default → Language primary model. Writer defaults to Language LLM instead.

**Supporting libraries** — `src/cw/lib/`:
- `config.py` — `PresetsConfig` loads `data/presets.json`
- `prompt_enhancer.py` — Three enhancers: rule-based (`PromptEnhancer`), local LLM (`HFPromptEnhancer` using Qwen2.5-3B), Anthropic API (`LLMPromptEnhancer`)
- `civitai.py` — Auto-download LoRAs from CivitAI by AIR URN
- `loras/manager.py` — LoRA filtering by base architecture and optional theme (e.g., 'anime', 'photorealistic', 'fantasy')
- `wvs.py` — World Values Survey parser: downloads from Kaggle via kagglehub, parses country-level cultural dimension profiles (Inglehart-Welzel axes, trust, tolerance, gender attitudes, civic participation), and transforms them into structured insights for Country records. Data flows automatically into the cultural research pipeline via `compose_insights_as_markdown()`.
- `controlnet_preprocessing.py` — ControlNet image preprocessing: `preprocess_image(image, control_type)` applies LineArt/Canny/Depth/SoftEdge/OpenPose detection via `controlnet_aux`. Detector instances cached for reuse.
- `storyboard.py` — `StoryboardGenerator` (text-based prompts), `WireframePromptBuilder` (style-focused prompts for ControlNet), `create_storyboard_jobs()`, `create_wireframe_storyboard_jobs()` (links keyframes → DiffusionJobs with ControlNet settings)
- `models/sdxl_controlnet.py` — `SDXLControlNetModel` (StableDiffusionXLControlNetPipeline)
- `models/sd15_controlnet.py` — `SD15ControlNetModel` (StableDiffusionControlNetPipeline)
- `pipeline/state.py` — `resolve_pipeline_models()` resolves per-node LLM models with fallback chain; `build_initial_state()` builds PipelineState from VideoAdUnit
- `pipeline/nodes.py` — `_get_generator(state, schema, node_key)` loads node-specific LLM via PipelineModelLoader singleton

### Data Flow

**Diffusion Workflow**:
1. User creates a `Prompt` and `DiffusionJob` via Django admin
2. Admin `save_model()` hook auto-queues the job to Celery
3. Worker loads model (with warm cache), optionally loads LoRA (auto-downloads from CivitAI if AIR set)
4. Images generated and saved to `media/diffusion/`
5. Job status updated, results viewable in admin with image previews

**TV Spot Adaptation Workflow**:
1. User creates a `Campaign` with original script JSON and origin `VideoAdUnit`
2. User creates adaptation `VideoAdUnit` selecting target Region/Country/Language, Brand/Persona, and optional per-node LLM model overrides
3. Admin `save_model()` hook auto-queues `create_adaptation_task` to Celery (if `use_pipeline=True`)
4. Multi-agent pipeline executes via LangGraph:
   - Concept extraction: Analyzes origin script for core themes, emotions, narrative structure
   - Cultural research: Investigates target culture's values, communication styles, taboos
   - Script writing: Adapts script with culturally-appropriate visuals and dialogue
   - Format evaluation: Verifies descriptions are in English, only VO/supers in target language with translations
   - Cultural evaluation: Validates cultural sensitivity and appropriateness
   - Concept evaluation: Ensures adapted script preserves original campaign intent
   - Brand evaluation: Verifies brand voice, values, visual identity, and messaging consistency
   - Revision loop: Rewrites script if any evaluation fails (max 3 retries per gate)
5. Pipeline saves `concept_brief`, `cultural_brief`, `evaluation_history` to VideoAdUnit
6. Adapted script rows saved as `AdUnitScriptRow` records
7. User creates `Storyboard` for the adapted VideoAdUnit
8. `generate_storyboard_task` generates image prompts and creates `DiffusionJob` records
9. Storyboard images viewable in admin with inline frame previews

**Wireframe Storyboard Workflow** (ControlNet):
1. User uploads MP4 video → `analyze_video_task` extracts scenes, keyframes, transcription
2. Origin `VideoAdUnit` created from video analysis with `AdUnitMedia` linking to `VideoProcessingResult` → `KeyFrame` records
3. User opens "Generate Storyboard" for the VideoAdUnit, selects "Keyframe (Wireframe)" source type
4. Selects ControlNet model (architecture must match diffusion model), optional preprocessing override, conditioning scale, guidance end, style prompt
5. Admin dispatches `generate_wireframe_storyboard_task` instead of text-based task
6. Task matches KeyFrames (by `scene_number`) to `AdUnitScriptRow` (by `shot_number`), creates `DiffusionJob` records with ControlNet settings and keyframe images as `reference_image`
7. `generate_images_task` preprocesses reference images (LineArt/Canny/Depth), then generates wireframe cels via ControlNet-guided diffusion
8. Results stored as `StoryboardImage` records with `key_frame` FK for source tracking

### Reference Data Architecture

**Separate JSON Files Per Model** (Implemented 2026-02):
```
data/
├── llm_models.json          # LLM models for text generation
├── regions.json             # Geographic regions (DACH, EU-WEST, LATAM, etc.)
├── countries.json           # Countries with default language references
├── languages.json           # Languages with primary/alternative model references
├── country_regions.json     # M2M: Country → Region mappings
├── country_languages.json   # M2M: Country → Language mappings (with is_primary)
└── brands.json              # Brand reference data (voice, guidelines, insights)
```

**Relationship Handling via Codes/IDs**:
- `languages.json` references `primary_model` by `model_id` (e.g., "Qwen/Qwen2.5-7B-Instruct")
- `countries.json` references `default_language` by language `code` (e.g., "en-US")
- M2M files use `country_code`, `region_code`, `language_code` for references

**Import/Export Commands**:
- `export_reference_data` — Exports all reference data to 6 separate JSON files
- `import_reference_data` — Imports in dependency order: LLM Models → Regions → Countries → Languages → M2M
- Both commands support `--dir` for custom directory and `--dry-run` for preview

**Import Dependency Order**:
1. LLM Models (no dependencies)
2. Regions (no dependencies)
3. Countries (optional FK to Language, resolved after Languages import if missing)
4. Languages (FK to LLM Model for primary_model)
5. Country-Region mappings (FKs to Country, Region)
6. Country-Language mappings (FKs to Country, Language)

### Configuration
- `data/presets.json` — Master config for models and LoRAs (synced to DB via `import_presets`)
- `data/*.json` — Reference data (regions, countries, languages, LLM models) in separate files
- `.env` — Environment variables:
  - **Required**: `POSTGRES_*`, `VALKEY_*`, `DJANGO_SECRET_KEY`
  - **Optional**: `ANTHROPIC_API_KEY` (for LLM prompt enhancement), `CIVITAI_API_KEY` (for auto-downloading LoRAs), `KAGGLE_API_TOKEN` (for downloading WVS dataset via kagglehub), `MODEL_BASE_PATH` (base directory for local `.safetensors` files)
- `src/cw/settings.py` — Django settings including Celery config and Unfold admin setup
- `grafana/provisioning/` — Grafana datasource/dashboard provisioning (auto-configures Loki on startup)

### Prompt Templates

**Database-Only LLM Prompts** (since Issue #50):
LLM prompts are stored exclusively in the `PromptTemplate` model (database-only, no filesystem fallback). This enables live editing via Django admin without code deployment.

- Templates loaded from `PromptTemplate` model by slug (e.g., `"adaptation"`, `"eval-brand"`)
- Results cached in Redis/memory (5-minute TTL)
- Usage analytics tracked (`usage_count`, `last_used_at`)
- Editable via Django admin at `/admin/prompts/prompttemplate/`
- Template source of truth for bootstrapping: `data/prompt_templates.json`

**Template Versioning**:
- Each template edit creates a new version (auto-incrementing `version` number)
- Only one version per slug can be `is_active=True` at a time
- Old versions retained for rollback/audit trail

**Management Commands**:
```bash
uv run manage.py import_prompt_templates   # Import from data/prompt_templates.json to database
uv run manage.py import_prompt_templates --dry-run  # Preview import
uv run manage.py export_prompt_templates   # Export active templates to data/prompt_templates.json
```

**Usage**:
```python
from cw.lib.prompts import render_prompt

# Always use the DB slug (hyphenated)
prompt = render_prompt("adaptation", target_market_name="Japan", ...)
prompt = render_prompt("eval-brand", adapted_script_json=data, ...)
```

**Current Templates** (9 total):
| Slug | Name | Category | Usage |
|------|------|----------|-------|
| `prompt-enhancer-system` | Prompt Enhancer System | enhancement | System prompt for HF/Anthropic enhancers |
| `prompt-enhancer-user` | Prompt Enhancer User | enhancement | User prompt for enhancement requests |
| `adaptation` | Cultural Adaptation | adaptation | Main TV spot localization prompt (104 lines) |
| `concept-extraction` | Concept Extraction | concept | Analyzes original script for core concept |
| `cultural-research` | Cultural Research | concept | Produces cultural brief for target market |
| `eval-concept` | Concept Evaluation | evaluation | Evaluates concept fidelity |
| `eval-cultural` | Cultural Evaluation | evaluation | Evaluates cultural appropriateness |
| `eval-format` | Format Evaluation | evaluation | Evaluates language compliance |
| `eval-brand` | Brand Evaluation | evaluation | Evaluates brand consistency and guidelines |

**Editing Prompts**:
1. Navigate to Django admin → Prompt Templates
2. Select template to edit3. Modify `template` field (Jinja2 syntax validated on save)
4. Save → auto-creates new version and invalidates cache
5. Changes take effect immediately (no deployment needed)

**Location**: `src/cw/prompts/` (Django app), `src/cw/lib/prompts/__init__.py` (render_prompt())

### Model-Specific Notes
| Model | Pipeline | Steps | CFG | Negative Prompt | Architecture |
|-------|----------|-------|-----|-----------------|--------------|
| Z-Image Turbo | ZImagePipeline | 9 | 0.0 | No | zimage |
| Flux.1-dev | FluxPipeline | 28 | 3.5 | No | flux1 |
| Qwen-Image-2512 | QwenImagePipeline | 50 | 4.5 | Yes | qwen |
| SDXL Turbo | AutoPipelineForText2Image | 4 | 0.0 | No | sdxl |
| Juggernaut XL v9 | StableDiffusionXLPipeline | 30 | 7.0 | Yes | sdxl |
| DreamShaper XL Lightning | StableDiffusionXLPipeline | 4 | 2.0 | No | sdxl |
| Realistic Vision v5.1 | StableDiffusionPipeline | 30 | 5.0 | Yes | sd15 |
| SDXL + ControlNet | StableDiffusionXLControlNetPipeline | 30 | 7.0 | Yes | sdxl |
| SD1.5 + ControlNet | StableDiffusionControlNetPipeline | 30 | 5.0 | Yes | sd15 |

### ControlNet Integration

**ControlNet** provides structural guidance (edges, depth, poses) for image generation. Used primarily for wireframe storyboard generation from video keyframes.

**Control Types**: `canny` (edge detection), `lineart` (line art), `lineart_anime` (anime-style), `depth` (MiDaS depth), `softedge` (HED), `openpose` (pose estimation)

**Data Flow**: `KeyFrame.image` → `controlnet_preprocessing.preprocess_image()` → ControlNet pipeline → wireframe cel

**Key Files**:
- `src/cw/diffusion/models.py` — `ControlNetModel` (Django model), `DiffusionJob` ControlNet fields
- `src/cw/lib/controlnet_preprocessing.py` — Preprocessing via `controlnet_aux`
- `src/cw/lib/models/sdxl_controlnet.py` / `sd15_controlnet.py` — Pipeline implementations
- `src/cw/lib/storyboard.py` — `WireframePromptBuilder`, `create_wireframe_storyboard_jobs()`
- `src/cw/tvspots/tasks.py` — `generate_wireframe_storyboard_task()`

**Management Commands**:
```bash
uv run manage.py import_controlnets      # Sync data/controlnets.json → database
uv run manage.py export_controlnets      # Export ControlNet models to JSON
```

### Path Resolution
- Local models/LoRAs: path ends with `.safetensors` → resolved as `{base_model_path}/{path}`, loaded via `from_single_file()`
- HuggingFace models: path starts with `Hugginface:` or `Huggingface:` → prefix stripped, loaded via `from_pretrained()`

### Adding New Models (Post-Refactoring)

**Simple models** (most cases) - Just 10-20 lines:
1. Create `src/cw/lib/models/newmodel.py` inheriting from `BaseModel`
2. Override `_create_pipeline()` to return your pipeline instance
3. Add to `src/cw/lib/models/__init__.py` exports and `ModelFactory.create_model()`
4. Add model config to `data/presets.json` with appropriate flags
5. Run `uv run manage.py import_presets` to sync to database

**Example:**
```python
from diffusers import YourPipeline
from .base import BaseModel

class YourModel(BaseModel):
    def _create_pipeline(self):
        return YourPipeline.from_pretrained(
            self.model_path,
            torch_dtype=self.dtype,
        )
```

**Models with special requirements**:
- **Long prompts + prompt weighting** (CLIP-based models): Inherit from `CompelPromptMixin` + `BaseModel` (handles >77 tokens via Compel, supports `(word:weight)` syntax)
- **Token truncation** (legacy): Inherit from `CLIPTokenLimitMixin` + `BaseModel` (simple 77-token truncation, deprecated in favor of CompelPromptMixin)
- **Debug logging**: Inherit from `DebugLoggingMixin` + `BaseModel`
- **Custom prompt handling**: Override `_build_prompts(params: Dict) -> Dict`
- **Custom pipeline kwargs**: Override `_build_pipeline_kwargs(params: Dict, callback) -> Dict`
- **Custom device optimizations**: Override `_apply_device_optimizations() -> None`
- **Special prompt requirements**: Override `_handle_special_prompt_requirements(params: Dict) -> Dict`

### Compel Prompt Features (SDXL, SD15)

CLIP-based models (SDXL, SD15) now use [Compel](https://github.com/damian0815/compel) for advanced prompt handling:

**Long Prompts**: No 77-token limit - prompts are automatically chunked and embeddings concatenated:
```python
# This long prompt works without truncation:
prompt = """a highly detailed, photorealistic landscape painting of a serene mountain
valley at sunset, with dramatic lighting, golden hour atmosphere, misty background,
lush green meadows in the foreground, snow-capped peaks in the distance"""
```

**Prompt Weighting**: Emphasize or de-emphasize concepts using `(word:weight)` syntax:
```python
# Increase emphasis (>1.0) or decrease (<1.0):
prompt = "a (beautiful:1.3) landscape with (dramatic lighting:1.5), avoiding (blur:0.5)"
```

**LoRA Integration**: Trigger words are automatically appended without truncation concerns.

## Environment & Dependencies
- Python 3.12+ managed via `uv`
- All models use `torch.bfloat16` precision
- Apple Silicon: MPS backend with `enable_sequential_cpu_offload()` and `enable_attention_slicing()`
- One model loaded at a time (module-level `_model_cache` in tasks.py)
- `torch.mps.empty_cache()` called after each generation
