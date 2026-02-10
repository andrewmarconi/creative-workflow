.. meta ::
   :title: Generative Creative Lab

.. rst-class:: hidden-title

Generative Creative Lab
=======================

.. image:: _static/logo-wide.png
   :alt: Generative Creative Lab
   :align: center

A modular framework for creative development, exploration, and experimentation using generative AI.
---------------------------------------------------------------------------------------------------

Generative Creative Lab is a flexible platform designed for creative experimentation with generative AI models. Built on `Django <https://www.djangoproject.com/>`_, `Celery <https://docs.celeryq.dev/>`_, and `LangGraph <https://langchain-ai.github.io/langgraph/>`_, it provides a modular architecture for multi-model diffusion image generation using `HuggingFace <https://huggingface.co/>`_ pipelines, multi-agent cultural adaptation of TV scripts, dynamic prompt enhancement, and systematic creative exploration through model composition and workflow orchestration.

Key Capabilities
----------------

**Visual Asset Generation**
   Create concept imagery and storyboard frames using state-of-the-art AI image generation.
   Experiment with multiple visual styles, refine creative direction through iterative prompt
   development, and apply style treatments to maintain brand consistency across assets.

**TV Spot Localization & Adaptation**
   Explore how origin scripts translate across markets and cultures. The platform drafts
   localized variations that account for cultural nuances, regional sensitivities, and
   local context—giving creative teams a starting point for refinement. Generate visual
   storyboards for each variation to accelerate internal concepting and client discussions.

Citing This Software
====================

If you use this software in your research, please cite it using the following BibTeX entry:

.. code-block:: bibtex

   @misc{marconi2026generativecreativelab,
     author       = {Andrew Marconi},
     title        = {Generative Creative Lab},
     year         = {2026},
     howpublished = {\url{https://andrewmarconi.github.io/generative-creative-lab}},
     note         = {Interactive web project},
   }

| **Marconi, A.** (2026). *Generative Creative Lab* [Interactive web project].
| Retrieved from https://andrewmarconi.github.io/generative-creative-lab


.. toctree::
   :maxdepth: 2
   :caption: About
   :hidden:

   about/philosophy
   research/index
   about/roadmap


.. toctree::
   :maxdepth: 2
   :caption: User Documentation
   :hidden:

   user/quickstart
   user/guides/index
   user/segmentation
   user/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation
   :hidden:

   developer/architecture
   developer/data-schemas
   developer/contributing
   developer/api/index

.. toctree::
   :maxdepth: 2
   :caption: Project
   :hidden:

   project-changelog
