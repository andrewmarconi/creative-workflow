Library Modules (cw.lib)
========================

The ``cw.lib`` package contains reusable library modules for model loading,
prompt enhancement, LoRA management, and more.

Models
------

Factory and base classes for diffusion model implementations.

.. automodule:: cw.lib.models
   :members:
   :undoc-members:
   :show-inheritance:

Base Model
~~~~~~~~~~

Abstract base class implementing the template method pattern for all models.

.. automodule:: cw.lib.models.base
   :members:
   :undoc-members:
   :show-inheritance:

Model Mixins
~~~~~~~~~~~~

Reusable mixins for shared functionality across models.

.. automodule:: cw.lib.models.mixins
   :members:
   :undoc-members:
   :show-inheritance:

Configuration
-------------

Configuration loading and management from presets.json.

.. automodule:: cw.lib.config
   :members:
   :undoc-members:
   :show-inheritance:

Prompt Enhancement
------------------

Multiple prompt enhancement strategies: rule-based, local LLM, and Anthropic API.

.. automodule:: cw.lib.prompt_enhancer
   :members:
   :undoc-members:
   :show-inheritance:

CivitAI Integration
-------------------

Auto-download and management of LoRA models from CivitAI.

.. automodule:: cw.lib.civitai
   :members:
   :undoc-members:
   :show-inheritance:

LoRA Management
---------------

LoRA filtering and application by base architecture and theme.

.. automodule:: cw.lib.loras.manager
   :members:
   :undoc-members:
   :show-inheritance:

Adaptation
----------

Market adaptation and localization for TV spot content.

.. automodule:: cw.lib.adaptation
   :members:
   :undoc-members:
   :show-inheritance:

Storyboard
----------

Storyboard generation from scripts.

.. automodule:: cw.lib.storyboard
   :members:
   :undoc-members:
   :show-inheritance:
