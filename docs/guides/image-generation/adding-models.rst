Adding a New Model
==================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How to add a new diffusion model to the system.

Planned content:

- Create a model file in ``src/cw/lib/models/``
- Implement ``_create_pipeline()`` (the only required override)
- Register in ``ModelFactory.create_model()`` in ``__init__.py``
- Add model configuration to ``data/presets.json``
- Run ``import_presets`` to sync to database
- Simple model example (~20 lines)
- Complex model example (custom prompts, device optimizations, mixins)
