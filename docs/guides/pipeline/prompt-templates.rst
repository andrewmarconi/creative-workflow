Prompt Template Editing
=======================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How to edit LLM prompts used by the adaptation pipeline.

Planned content:

- Navigate to Django admin → Prompt Templates
- Jinja2 template syntax and validation on save
- Template versioning: auto-incremented, one active version per slug
- Variable reference for each template (9 templates, 4 categories)
- Cache invalidation: changes take effect within 5 minutes (Redis/memory TTL)
- Usage analytics: ``usage_count``, ``last_used_at``
- Import/export: ``import_prompt_templates``, ``export_prompt_templates``
- Source of truth: ``data/prompt_templates.json``
