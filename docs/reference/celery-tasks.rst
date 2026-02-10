Celery Tasks & Queues
=====================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

Reference for all Celery tasks and queue configuration.

Planned content:

- **Tasks**:

  - ``enhance_prompt_task(prompt_id)`` — Prompt enhancement (enhancement queue)
  - ``generate_images_task(job_id)`` — Image generation (default queue)
  - ``create_adaptation_task(video_ad_unit_id)`` — Multi-agent pipeline (default queue)
  - ``generate_storyboard_task(storyboard_id)`` — Storyboard generation (default queue)

- **Queues**: ``default``, ``enhancement``
- **Worker configuration**: ``solo`` pool (single-threaded for GPU safety)
- **Time limits**: 3600s hard, 3300s soft
- **Task routing rules**
- **Result storage**: Django ORM via ``django-celery-results``
- **Retry behavior and error handling**
- **Module-level model caching** (warm cache between tasks)
