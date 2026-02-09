# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Audience Segmentation System**: Comprehensive audience segmentation framework (#49)
  - Segment model with three categories: DEMOGRAPHIC, BEHAVIORAL, PSYCHOGRAPHIC
  - 3,457 predefined segments based on industry frameworks (VALS, Rogers' Innovation Adoption Curve, AIO variables)
  - Persona model for combining geographic and non-geographic segments
  - JSON schemas for segments, personas, and persona-segment mappings
  - Import/export management commands (`import_segments`, `export_segments`, `import_personas`, `export_personas`)
  - Complete user documentation (`docs/user/segmentation.rst`) with theoretical frameworks and best practices
  - Developer schema reference (`docs/developer/data-schemas.rst`) with validation rules and examples
- CONTRIBUTING.md with contribution guidelines and code style (#13)
- CHANGELOG.md for version tracking (#14)

## [0.2.0] - 2026-02-08

### Added
- **TV Spot Adaptation System**: Multi-agent pipeline for culturally adapting TV commercials
  - Campaign→VideoAdUnit domain model architecture
  - Region→Country→Language reference data hierarchy
  - LangGraph-based adaptation pipeline with concept extraction, cultural research, script writing, and evaluation agents
  - Format/language compliance evaluation node for script validation
  - Storyboard generation from adapted scripts
- **Tailwind CSS 4 Build Pipeline**: Structured insights editor widget with modern CSS tooling
- **Flower Task Monitor**: Real-time Celery task monitoring on port 5555
- **Grafana + Loki Integration**: Log aggregation and search via Grafana UI (port 3000)
  - Alloy-based log collection from `logs/*.log`
  - Automatic Loki datasource provisioning
- **Reference Data Management**: Separate JSON files for regions, countries, languages, LLM models
  - `export_reference_data` command with `--dir` and `--dry-run` support
  - `import_reference_data` command with dependency-aware import ordering
- **Homepage Links**: Navigation shortcuts in admin interface
- **Django Unfold Admin**: Modern admin interface with custom templates

### Changed
- **Celery Queue Architecture**: Consolidated to single `default` queue with `solo` pool
  - Sequential task execution prevents concurrent model loading
  - Natural task batching for storyboard generation
  - Improved GPU memory efficiency
- **TV Spot Model Refactoring**: Migrated from separate Origin/Adaptation models to unified VideoAdUnit with polymorphic AdUnit base (#46)
  - Adaptation chain via `source_ad_unit` FK
  - Pipeline integration with status tracking and JSON brief storage
  - Multi-table inheritance for extensibility
- **Logging Architecture**: Structured JSON logging with per-worker log files
  - `logs/tasks.log` - All task execution
  - `logs/worker_default.log` - Image generation worker
  - `logs/django.log` - Django server
  - `logs/celery.log` - Celery general logs
- **Documentation Updates**: CLAUDE.md updated to match refactored architecture

### Fixed
- CUDA OOM errors on storyboard generation via sequential model loading
- CSS path references in VideoAdUnit admin
- Pipeline nodes compatibility with VideoAdUnit model
- Language models API endpoint and template variables
- Missing `format_evaluation` status in admin UI

### Removed
- Separate enhancement worker queue (consolidated into default queue)
- AdaptationMarket model (replaced by Region→Country→Language)
- Origin/Adaptation separate models (unified into VideoAdUnit)

## [0.1.0] - 2026-02-05

### Added
- **Multi-Model Diffusion Support**: 7 models with varying architectures
  - Z-Image Turbo (zimage)
  - Flux.1-dev (flux1)
  - Flux 2 Klein (flux2)
  - Qwen-Image-2512 (qwen)
  - SDXL Turbo (sdxl)
  - DreamShaper XL Lightning (sdxl)
  - Juggernaut XL v9 (sdxl)
  - Realistic Vision v5.1 (sd15)
- **Model Architecture Refactoring**: Template Method Pattern for DRY code
  - `BaseModel` abstract base with concrete template methods
  - `CompelPromptMixin` for long prompt handling (>77 tokens) and prompt weighting
  - `CLIPTokenLimitMixin` for legacy 77-token truncation
  - `DebugLoggingMixin` for debug output
  - Minimal concrete implementations (20-70 lines per model)
  - Configuration-driven behavior via `data/presets.json`
- **Compel Prompt Features**: Advanced prompt handling for CLIP-based models (SDXL, SD15)
  - Automatic prompt chunking for >77 tokens
  - Prompt weighting syntax: `(word:weight)`
  - LoRA trigger word integration without truncation
- **LoRA Management**: Dynamic LoRA loading with theme-based filtering
  - Auto-download from CivitAI by AIR URN
  - Theme categorization (anime, photorealistic, fantasy)
  - Base architecture compatibility checking
- **Prompt Enhancement**: Three enhancement strategies
  - Rule-based (`PromptEnhancer`)
  - Local LLM (`HFPromptEnhancer` using Qwen2.5-3B)
  - Anthropic API (`LLMPromptEnhancer`)
- **Jinja2 Prompt Templates**: Template-based LLM prompts for adaptation pipeline
  - Structured prompt composition
  - Variable interpolation
  - Reusable prompt components
- **Django Admin Interface**: Django Unfold-based UI
  - Prompt and job management
  - Image previews and downloads
  - Model and LoRA configuration
  - Storyboard inline frame previews
- **Celery Task Processing**: Async image generation and prompt enhancement
  - Model warming and caching
  - Sequential task execution
  - Task result persistence
- **Sphinx Documentation**: Comprehensive project documentation
  - Architecture overview
  - API reference
  - Development guides
  - HTML documentation build with `make html`
- **Src Layout**: Proper Python packaging structure
  - `src/cw/` package directory
  - Clean separation of source and project root
  - Improved import resolution
- **Configuration Management**: JSON-based configuration system
  - `data/presets.json` for models and LoRAs
  - `import_presets`/`export_presets` commands
  - Environment variable support via `.env`
- **Docker Compose Setup**: Containerized dependencies
  - PostgreSQL 17 (port 5435)
  - Valkey/Redis (port 6379)
  - Grafana (port 3000)
  - Loki (port 3100)
- **Development Tooling**:
  - `uv` for fast dependency management
  - `honcho` for process orchestration
  - `Procfile` for service definitions
  - `./start.sh` for ordered startup

### Changed
- **Device Optimization**: Platform-specific optimizations
  - Apple Silicon: MPS backend with sequential CPU offload
  - CUDA: Configurable CPU offload strategies
  - Automatic attention slicing
  - Model caching for warm restarts
- **Precision**: All models use `torch.bfloat16` for efficiency

### Migration Notes

#### Model Architecture Refactoring
**Before (0.0.x)**: Each model had duplicate code for loading, generation, LoRA management (~200-300 lines per model).

**After (0.1.0)**: Models inherit from `BaseModel` and mixins, only overriding specific hooks (~20-70 lines per model).

**Migration**: No user-facing changes. Model behavior remains the same, but new models are much easier to add.

#### Src Layout Adoption
**Before (0.0.x)**: Code lived directly in repository root.

**After (0.1.0)**: Code lives in `src/cw/` package.

**Migration**: If importing directly, update imports from `cw.module` to `cw.module` (no change needed if using Django app imports).

#### Compel Prompt Support
**Before (0.0.x)**: SDXL/SD15 models truncated prompts at 77 tokens.

**After (0.1.0)**: Automatic chunking and concatenation for unlimited prompt length, plus `(word:weight)` syntax support.

**Migration**: Existing prompts work unchanged. Long prompts will no longer be truncated. Optionally use weighting syntax for emphasis.

---

## Version History

- **[Unreleased]** - In development
- **[0.2.0]** - 2026-02-08 - TV Spot Adaptation System
- **[0.1.0]** - 2026-02-05 - Initial release with multi-model diffusion

[Unreleased]: https://github.com/andrewmarconi/generative-creative-lab/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/andrewmarconi/generative-creative-lab/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/andrewmarconi/generative-creative-lab/releases/tag/v0.1.0
