Generative Creative Lab
=======================

.. image:: _static/logo-wide.png
   :alt: Generative Creative Lab
   :align: center

A modular framework for creative development, exploration, and experimentation using generative AI.
---------------------------------------------------------------------------------------------------

Generative Creative Lab is a flexible platform designed for creative experimentation with generative AI models. Built on `Django <https://www.djangoproject.com/>`_, `Celery <https://docs.celeryq.dev/>`_, `HugggingFace <https://huggingface.co/>`_, and `LangGraph <https://langchain-ai.github.io/langgraph/>`_, it provides a modular architecture for multi-model diffusion image generation, pipelines, multi-agent cultural adaptation of TV scripts, dynamic prompt enhancement, and systematic creative exploration through model composition and workflow orchestration.

.. rubric:: Key Capabilities

- **Multi-Model Diffusion** — 7+ models (Flux, SDXL, Qwen, Z-Image) with LoRA support, prompt enhancement, and Compel weighting
- **Cultural Adaptation Pipeline** — LangGraph multi-agent system that adapts TV spots for target markets with evaluation gates
- **Audience Targeting** — Geographic (Region/Country/Language) and non-geographic (Demographic/Behavioral/Psychographic) segmentation with persona composition

----

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Getting Started

   getting-started/installation
   getting-started/first-image
   getting-started/first-adaptation

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Concepts

   concepts/for-marketers
   concepts/architecture
   concepts/diffusion-models
   concepts/adaptation-pipeline
   concepts/audience-targeting
   concepts/observability

.. toctree::
   :maxdepth: 2
   :hidden:
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
   :hidden:
   :caption: Reference

   reference/management-commands
   reference/data-schemas
   reference/model-specifications
   reference/configuration
   reference/celery-tasks
   reference/api/index

.. toctree::
   :maxdepth: 2
   :hidden:
   :caption: Project

   project/philosophy
   project/contributing
   project/roadmap
   project/research-notes
   project/changelog
   project/license
