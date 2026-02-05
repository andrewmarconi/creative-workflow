Diffusion App (cw.diffusion)
============================

The ``cw.diffusion`` Django app handles diffusion model management, prompt
storage, and image generation job execution.

Models
------

Django ORM models for DiffusionModel, LoraModel, Prompt, and DiffusionJob.

.. automodule:: cw.diffusion.models
   :members:
   :undoc-members:
   :show-inheritance:

Tasks
-----

Celery tasks for async image generation and prompt enhancement.

.. automodule:: cw.diffusion.tasks
   :members:
   :undoc-members:
   :show-inheritance:

Admin
-----

Django Unfold admin configuration for the diffusion app.

.. automodule:: cw.diffusion.admin
   :members:
   :undoc-members:
   :show-inheritance:
