Roadmap
=======

Development status, priorities, and future direction.

Completed
---------

Core Platform
^^^^^^^^^^^^^

- Multi-model diffusion image generation (7 models)
- Template Method architecture with BaseModel + mixins (`#1 <https://github.com/andrewmarconi/generative-creative-lab/issues/1>`_)
- LoRA management with CivitAI auto-download
- Compel prompt weighting for CLIP-based models
- Three prompt enhancement strategies (rule-based, local LLM, Anthropic API)
- Django Unfold admin interface
- Celery task processing with solo pool and model caching
- Configuration-driven behavior via presets.json
- Code style enforcement with flake8 (`#15 <https://github.com/andrewmarconi/generative-creative-lab/issues/15>`_)
- Claude Code consistency check skill (`#22 <https://github.com/andrewmarconi/generative-creative-lab/issues/22>`_)

TV Spot Adaptation
^^^^^^^^^^^^^^^^^^

- Campaign and VideoAdUnit domain model (`#47 <https://github.com/andrewmarconi/generative-creative-lab/issues/47>`_)
- LangGraph multi-agent adaptation pipeline --- 7 nodes (`#26 <https://github.com/andrewmarconi/generative-creative-lab/issues/26>`_)
- Four evaluation gates --- format (`#48 <https://github.com/andrewmarconi/generative-creative-lab/issues/48>`_), cultural, concept, brand (`#45 <https://github.com/andrewmarconi/generative-creative-lab/issues/45>`_)
- Storyboard generation from adapted scripts
- Video upload and 10-phase analysis (`#53 <https://github.com/andrewmarconi/generative-creative-lab/issues/53>`_)
- Per-node LLM model selection with fallback chains
- Database-backed prompt templates with versioning (`#50 <https://github.com/andrewmarconi/generative-creative-lab/issues/50>`_)

Reference Data
^^^^^^^^^^^^^^

- Region / Country / Language hierarchy with insights (`#44 <https://github.com/andrewmarconi/generative-creative-lab/issues/44>`_)
- Language and LLM model database models (`#23 <https://github.com/andrewmarconi/generative-creative-lab/issues/23>`_)
- Audience segments --- demographic, behavioral, psychographic (`#49 <https://github.com/andrewmarconi/generative-creative-lab/issues/49>`_)
- Personas combining geographic and segment targeting (`#49 <https://github.com/andrewmarconi/generative-creative-lab/issues/49>`_)
- Brand reference data with guidelines and structured insights (`#45 <https://github.com/andrewmarconi/generative-creative-lab/issues/45>`_)
- Structured JSON import/export for all reference data (`#20 <https://github.com/andrewmarconi/generative-creative-lab/issues/20>`_)

Infrastructure
^^^^^^^^^^^^^^

- Grafana + Loki + Alloy log aggregation (`#19 <https://github.com/andrewmarconi/generative-creative-lab/issues/19>`_)
- Structured JSON logging with rotating file handlers
- Docker Compose for PostgreSQL, Valkey, and observability stack
- Sphinx documentation with Mermaid diagrams and autodoc
- Diataxis documentation restructuring (`#61 <https://github.com/andrewmarconi/generative-creative-lab/issues/61>`_)

Current Priorities
------------------

- LoRA + storyboard pipeline generates black images on MPS (`#60 <https://github.com/andrewmarconi/generative-creative-lab/issues/60>`_)
- Video (MP4) analysis --- pipeline for analyzing video files and extracting concept, culture and audience as well as building storyboards (`#75 <https://github.com/andrewmarconi/generative-creative-lab/issues/75>`_)
- Add pytest-django test framework and initial test coverage (`#17 <https://github.com/andrewmarconi/generative-creative-lab/issues/17>`_)
- Refactor moderate complexity functions (`#16 <https://github.com/andrewmarconi/generative-creative-lab/issues/16>`_)
- Add type hints to helper functions and core modules (`#18 <https://github.com/andrewmarconi/generative-creative-lab/issues/18>`_)
- Pipeline reliability improvements --- evaluation gate tuning (`#76 <https://github.com/andrewmarconi/generative-creative-lab/issues/76>`_)

Future Ideas
------------

These are potential directions, not commitments:

- **AudioAdUnit / PrintAdUnit** --- extend polymorphic AdUnit for non-video formats (`#24 <https://github.com/andrewmarconi/generative-creative-lab/issues/24>`_)
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
