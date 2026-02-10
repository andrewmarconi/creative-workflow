Generative Creative Lab
=======================

A Django + Celery application for multi-model diffusion image generation, multi-agent TV spot cultural adaptation, and audience targeting.

.. rubric:: Key Capabilities

- **Multi-Model Diffusion** — 7+ models (Flux, SDXL, Qwen, Z-Image) with LoRA support, prompt enhancement, and Compel weighting
- **Cultural Adaptation Pipeline** — LangGraph multi-agent system that adapts TV spots for target markets with evaluation gates
- **Audience Targeting** — Geographic (Region/Country/Language) and non-geographic (Demographic/Behavioral/Psychographic) segmentation with persona composition

----

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/installation
   getting-started/first-image
   getting-started/first-adaptation

.. toctree::
   :maxdepth: 2
   :caption: Concepts

   concepts/architecture
   concepts/diffusion-models
   concepts/adaptation-pipeline
   concepts/audience-targeting
   concepts/observability

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/image-generation/adding-models
   guides/image-generation/loras
   guides/image-generation/prompt-enhancement
   guides/image-generation/compel-weighting
   guides/tv-spot-adaptation/creating-campaigns
   guides/tv-spot-adaptation/ad-units
   guides/tv-spot-adaptation/importing-tvspots
   guides/tv-spot-adaptation/video-analysis
   guides/tv-spot-adaptation/storyboards
   guides/audiences-brands/regions-countries-languages
   guides/audiences-brands/segments-personas
   guides/audiences-brands/brand-configuration
   guides/pipeline/prompt-templates
   guides/pipeline/per-node-models
   guides/pipeline/pipeline-settings
   guides/operations/data-import-export
   guides/operations/grafana-logging
   guides/operations/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/management-commands
   reference/data-schemas
   reference/model-specifications
   reference/configuration
   reference/celery-tasks
   reference/api/index

.. toctree::
   :maxdepth: 2
   :caption: Project

   project/philosophy
   project/contributing
   project/roadmap
   project/research-notes
   project/changelog
