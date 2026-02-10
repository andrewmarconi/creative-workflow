Per-Node Model Selection
========================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How to assign different LLM models to individual pipeline nodes.

Planned content:

- Model resolution chain:

  1. AdUnit ``pipeline_model_config`` override (per-node)
  2. PipelineSettings node default
  3. PipelineSettings global default
  4. Language primary model
  5. Writer node special case: defaults to Language LLM instead

- Setting overrides at the AdUnit level via ``pipeline_model_config`` JSONField
- Setting defaults at the app level via PipelineSettings singleton
- Practical examples: using a stronger model for evaluation, a faster model for writing
