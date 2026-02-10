Storyboard Generation
=====================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How to generate visual storyboards from adapted scripts.

Planned content:

- Create a Storyboard: link VideoAdUnit to DiffusionModel + optional LoRA
- Configure images per script row
- How prompts are generated from script row visual descriptions
- ``generate_storyboard_task`` Celery task flow
- Progress tracking: ``progress_percent``, ``total_jobs``, ``completed_jobs``
- Status lifecycle: pending → processing → completed/failed
- Multiple storyboards per VideoAdUnit (different model/LoRA configurations)
- Viewing storyboard frames in the admin
