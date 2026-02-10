Roadmap
=======

Development status, priorities, and future direction.

Completed
---------

Core Platform
^^^^^^^^^^^^^

- Multi-model diffusion image generation (7 models)
- Template Method architecture with BaseModel + mixins
- LoRA management with CivitAI auto-download
- Compel prompt weighting for CLIP-based models
- Three prompt enhancement strategies (rule-based, local LLM, Anthropic API)
- Django Unfold admin interface
- Celery task processing with solo pool and model caching
- Configuration-driven behavior via presets.json

TV Spot Adaptation
^^^^^^^^^^^^^^^^^^

- Campaign and VideoAdUnit domain model
- LangGraph multi-agent adaptation pipeline (7 nodes)
- Four evaluation gates (format, cultural, concept, brand)
- Storyboard generation from adapted scripts
- Video upload and 10-phase analysis (metadata, scenes, transcription, objects, style, sentiment)
- Per-node LLM model selection with fallback chains

Reference Data
^^^^^^^^^^^^^^

- Region / Country / Language hierarchy with insights
- Audience segments (demographic, behavioral, psychographic)
- Personas combining geographic and segment targeting
- Brand reference data with guidelines and structured insights
- JSON import/export for all reference data

Infrastructure
^^^^^^^^^^^^^^

- Grafana + Loki + Alloy log aggregation
- Structured JSON logging with rotating file handlers
- Docker Compose for PostgreSQL, Valkey, and observability stack
- Sphinx documentation with Mermaid diagrams and autodoc

Current Priorities
------------------

- Documentation completion (Diataxis restructuring)
- Test coverage expansion
- Pipeline reliability improvements (evaluation gate tuning)

Future Ideas
------------

These are potential directions, not commitments:

- **AudioAdUnit / PrintAdUnit** --- extend polymorphic AdUnit for non-video formats
- **LLM-based script generation** --- full script writing from video analysis (currently MVP)
- **Batch adaptation** --- queue multiple market adaptations from a single origin
- **A/B prompt comparison** --- side-by-side comparison of different prompt strategies
- **Webhook notifications** --- notify external systems on task completion
- **Model benchmarking** --- automated quality comparison across models and settings
- **Prompt library** --- curated, searchable collection of effective prompts by category

Non-Goals
---------

Things this project deliberately does not aim to do:

- **Replace creative professionals** --- the system augments, not automates
- **Real-time generation** --- batch processing is acceptable; latency is not a priority
- **Multi-tenant SaaS** --- designed for single-team use with Django admin as the UI
- **Custom frontend** --- Django Unfold admin is the interface; no React/Vue/etc.
- **Model training** --- this is an inference and orchestration platform, not a training pipeline
