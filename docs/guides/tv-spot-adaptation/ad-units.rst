Origin & Adaptation Ad Units
============================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

Understanding the ad unit model and the origin-to-adaptation chain.

Planned content:

- Polymorphic AdUnit base class (VIDEO, AUDIO, PRINT types)
- VideoAdUnit: duration, visual style prompts, script management
- Origin vs. adaptation: the ``origin_or_adaptation`` field
- Source chain: ``source_ad_unit`` FK linking adaptations to their origin
- Script rows (``AdUnitScriptRow``): shot number, timecode, visual/audio content
- Pipeline status lifecycle (8 stages from concept_analysis to revising)
- Per-node model configuration via ``pipeline_model_config`` JSONField
