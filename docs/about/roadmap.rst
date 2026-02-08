Project Roadmap
================


Development Status
------------------

"Complete" and "Releases" are funny words to use with this project. The goal is not to create a finished product, but rather to build a flexible and extensible framework for experimentation and analysis that can evolve over time.

In that spirit, the project is currently in an active development phase, with regular updates and improvements being made. New features, models, and capabilities are continuously being integrated based on user feedback and emerging technologies in the generative AI space.

Completed Experiments
---------------------

- **Multi-Model Pipeline for Adaptations**: `GitHub Issue #26 <https://github.com/andrewmarconi/generative-creative-lab/issues/26>`_ A LangGraph-based multi-agent pipeline that orchestrates concept extraction, cultural research, script writing, and evaluation (format, cultural, concept) with revision loop-back capabilities. Implemented in ``cw.lib.pipeline``.
- **Expanded Context Metadata**: `GitHub Issue #44 <https://github.com/andrewmarconi/generative-creative-lab/issues/44>`_ Region/Country/Language reference data architecture replacing the flat market profile system, with per-entity cultural insights and LLM model recommendations.

Feature & Experiment Ideas
--------------------------

- **Audio Adaptation Workflow**: `GitHub Issue #24 <https://github.com/andrewmarconi/generative-creative-lab/issues/24>`_ Develop a workflow for adapting radio spot audio scripts across markets, combining AI-powered localization with text-to-speech generation for review-ready audio outputs.
- **Expanded Model Integrations**: `GitHub Issue #25 <https://github.com/andrewmarconi/generative-creative-lab/issues/25>`_ Build a flexible model integration framework that allows users to leverage diverse generative AI models for images, text, and multimodal tasks, matching the best tool to each creative challenge.
- **BrandAgent for Brand Consistency**: `GitHub Issue #45 <https://github.com/andrewmarconi/generative-creative-lab/issues/45>`_ Add a BrandAgent to the multi-agent adaptation workflow to enforce brand guidelines and consistency across adapted scripts.

Non-Goals
---------

- **Fully Refined User Interface**: This project is focused on developing techniques, workflows, and integrations rather than delivering a polished end-user application.
- **Production-Ready System**: While the platform is functional, it is not intended for production use. The emphasis is on experimentation and exploration rather than reliability and scalability.

Related Documentation
---------------------

- :doc:`/about/philosophy` - Project philosophy and principles
- :doc:`/user/guides/index` - User guides and tutorials
- :doc:`/developer/architecture` - Technical architecture