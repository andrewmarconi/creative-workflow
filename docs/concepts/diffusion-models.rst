Diffusion Models
================

.. admonition:: Stub
   :class: warning

   This page is a placeholder. Content to be written.

How the diffusion model system is designed and why.

Planned content:

- Template Method Pattern: BaseModel → Mixins → Concrete implementations
- Hook methods: ``_create_pipeline()``, ``_build_prompts()``, ``_build_pipeline_kwargs()``
- Mixins: CompelPromptMixin (long prompts + weighting), CLIPTokenLimitMixin, DebugLoggingMixin
- ModelFactory dispatcher and warm caching strategy
- Device optimization: MPS (Apple Silicon), CUDA, CPU offloading
- Configuration-driven behavior via ``presets.json`` flags
- When and why each model is suited for different creative tasks
