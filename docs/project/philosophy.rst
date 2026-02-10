Philosophy & Design Principles
===============================

Why this project exists and the principles that guide its development.

Vision
------

Generative Creative Lab is a platform for exploring how generative AI can augment human creativity in advertising production. The focus is on TV spot adaptation --- taking a single commercial and producing culturally-appropriate variations for global markets, using AI to handle the mechanical parts of localization while keeping creative direction in human hands.

Principles
----------

Creative AI Augments, Not Replaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

AI handles the repetitive, structured parts of the production workflow: generating image prompts from script descriptions, producing initial visual frames, and evaluating scripts against checklists. Creative direction, cultural judgment, and final approval remain with human operators.

Every automated step is reviewable in the admin interface before proceeding.

Multi-Model by Design
^^^^^^^^^^^^^^^^^^^^^

No single model is best for everything. The architecture supports 7+ diffusion models with different strengths:

- **Turbo models** (4--9 steps) for rapid iteration
- **Full models** (28--50 steps) for production quality
- **Specialized models** (Realistic Vision, Juggernaut XL) for specific visual styles

The same principle applies to LLM models: each pipeline node can use a different model optimized for its task.

Cultural Sensitivity as a First-Class Concern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The adaptation pipeline treats cultural context as structured data, not an afterthought:

- **Regions, Countries, Languages** form a hierarchical knowledge base with insights at each level
- **Audience segments and personas** feed demographic, behavioral, and psychographic context into adaptation
- **Four evaluation gates** (format, cultural, concept, brand) validate adapted scripts before acceptance
- **Brand guidelines** are checked against adapted content to maintain voice and identity across markets

Configuration Over Code
^^^^^^^^^^^^^^^^^^^^^^^^

Behavior changes should not require code changes wherever possible:

- **presets.json** defines model configurations and settings flags
- **Prompt templates** are database-backed Jinja2 with live editing, versioning, and cache invalidation
- **Reference data** (regions, countries, languages, segments, brands) is managed via JSON import/export
- **Per-node model selection** is configurable through admin without touching pipeline code
- **PipelineSettings** controls defaults from a singleton admin page

Template Method for Extensibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The model architecture uses the Template Method Pattern to keep concrete implementations minimal:

- **BaseModel** provides 90% of the logic (loading, generation, LoRA management, caching)
- Concrete models override only what differs (typically 20--70 lines)
- **Mixins** add optional behaviors (CLIP token handling, debug logging, prompt weighting)
- Adding a new model requires one file with one method override

This eliminates code duplication while remaining easy to understand.

Sequential Execution for GPU Safety
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Celery worker uses a solo pool (single-threaded) to prevent concurrent model loading. This is a deliberate architectural choice:

- Only one model occupies VRAM at a time
- Models are warm-cached between tasks for efficiency
- VRAM is explicitly freed when switching between model types (enhancer → diffusion → pipeline LLM)
- The trade-off is throughput for reliability --- a single worker handles all tasks sequentially

Database as Source of Truth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All operational data lives in the database, not the filesystem:

- Prompt templates are stored and versioned in the database (no filesystem fallback)
- Job status, metadata, and results are tracked in Django ORM
- Configuration is synced from JSON files to database via management commands
- The ``data/`` directory is the bootstrap source; the database is the runtime authority

Technical Foundations
---------------------

The project is built on:

- **Django 5 + Unfold** --- Admin-first UI, no custom frontend needed
- **Celery + Valkey** --- Async task processing with solo pool
- **HuggingFace Diffusers** --- Diffusion model abstraction
- **LangGraph** --- Multi-agent pipeline orchestration
- **Outlines** --- Structured LLM generation (Pydantic schema constraints)
- **Grafana + Loki** --- Log aggregation and search
- **Sphinx + Mermaid** --- Documentation with diagrams
