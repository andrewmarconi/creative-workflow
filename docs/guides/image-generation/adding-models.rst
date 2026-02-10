Adding a New Model
==================

This guide walks through adding a new diffusion model to the system, from creating the Python class to syncing configuration.

Prerequisites
-------------

Before starting, understand the model's requirements:

- **Pipeline class** — which ``diffusers`` pipeline loads it (e.g., ``FluxPipeline``, ``StableDiffusionXLPipeline``)
- **Text encoder** — CLIP-based (77-token limit, supports Compel) or non-CLIP
- **Default parameters** — recommended steps, guidance scale, resolution
- **Special requirements** — quantization, custom schedulers, prompt handling quirks

Step 1: Create the Model File
------------------------------

Create a new file in ``src/cw/lib/models/``. For a simple model, this is ~20 lines:

.. code-block:: python

   # src/cw/lib/models/newmodel.py

   from diffusers import YourPipeline
   from .base import BaseModel


   class NewModel(BaseModel):
       def _create_pipeline(self):
           return YourPipeline.from_pretrained(
               self.model_path,
               torch_dtype=self.dtype,
           )

``_create_pipeline()`` is the only required override. Everything else — device setup, generation loop, LoRA management, metadata, cache clearing — is inherited from ``BaseModel``.

Step 2: Register in the Factory
--------------------------------

Add the import and dispatch case to ``src/cw/lib/models/__init__.py``:

.. code-block:: python

   from .newmodel import NewModel

   class ModelFactory:
       @staticmethod
       def create_model(model_config: dict, model_path: str) -> BaseModel:
           pipeline_name = model_config.get("pipeline", "")

           # ... existing cases ...
           elif pipeline_name == "YourPipeline":
               return NewModel(model_config, model_path)
           else:
               raise ValueError(f"Unknown pipeline type: {pipeline_name}")

Also add ``NewModel`` to the ``__all__`` list.

Step 3: Add to presets.json
----------------------------

Add a model entry to the ``models`` array in ``data/presets.json``:

.. code-block:: json

   {
     "slug": "new-model",
     "label": "New Model",
     "pipeline": "YourPipeline",
     "path": "organization/model-name",
     "base_architecture": "sdxl",
     "settings": {
       "steps": 20,
       "guidance_scale": 7.0,
       "resolution": 1024,
       "dtype": "bfloat16",
       "supports_negative_prompt": false
     }
   }

Key fields:

- **slug** — unique identifier, used in the warm cache
- **pipeline** — must match the ``ModelFactory`` dispatch string
- **path** — HuggingFace repo ID (e.g., ``black-forest-labs/FLUX.1-dev``) or local ``.safetensors`` path
- **base_architecture** — determines LoRA compatibility (``sdxl``, ``sd15``, ``flux1``, ``qwen``, ``zimage``)
- **settings** — default generation parameters and behavior flags

Step 4: Sync to Database
--------------------------

Run the import command to sync ``presets.json`` to the Django database:

.. code-block:: bash

   uv run manage.py import_presets

The model will appear in the Diffusion Models admin page and be available for DiffusionJob creation.

Adding Behavior with Hooks
--------------------------

For models that need custom behavior, override the optional hook methods:

.. code-block:: python

   from diffusers import SpecialPipeline
   from .base import BaseModel


   class SpecialModel(BaseModel):
       def _create_pipeline(self):
           return SpecialPipeline.from_pretrained(
               self.model_path,
               torch_dtype=self.dtype,
           )

       def _build_pipeline_kwargs(self, params, progress_callback):
           """Add model-specific generation parameters."""
           kwargs = super()._build_pipeline_kwargs(params, progress_callback)
           # Example: this model uses true_cfg_scale instead of guidance_scale
           kwargs["true_cfg_scale"] = kwargs.pop("guidance_scale")
           return kwargs

       def _handle_special_prompt_requirements(self, params):
           """Handle model-specific prompt quirks."""
           # Example: model requires non-empty negative prompt
           if not params.get("negative_prompt"):
               params["negative_prompt"] = " "
           return params

Available hooks (see :doc:`/concepts/diffusion-models` for details):

- ``_build_prompts(params)`` — customize prompt processing
- ``_build_pipeline_kwargs(params, callback)`` — add model-specific pipeline parameters
- ``_apply_device_optimizations()`` — custom device setup
- ``_handle_special_prompt_requirements(params)`` — model-specific prompt quirks

Adding Mixins
-------------

For CLIP-based models that need long prompt support or prompt weighting:

.. code-block:: python

   from diffusers import StableDiffusionXLPipeline
   from .base import BaseModel
   from .mixins import CompelPromptMixin


   class MySDXLModel(CompelPromptMixin, BaseModel):
       """SDXL model with Compel prompt weighting."""

       def _create_pipeline(self):
           return StableDiffusionXLPipeline.from_pretrained(
               self.model_path,
               torch_dtype=self.dtype,
               variant="fp16",
           )

Mixins must be listed **before** ``BaseModel`` in the class definition for proper MRO.

Available mixins:

- ``CompelPromptMixin`` — long prompts (>77 tokens) and ``(word:1.3)`` weighting for CLIP-based models
- ``DebugLoggingMixin`` — verbose debug output gated by the ``enable_debug_logging`` flag

Configuration Flags
-------------------

Control model behavior via flags in the ``settings`` block of ``presets.json``:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Flag
     - When to Use
   * - ``force_default_guidance: true``
     - Turbo/distilled models that must use CFG 0.0
   * - ``max_sequence_length: 512``
     - Models with non-CLIP text encoders (Flux, Flux 2 Klein)
   * - ``load_in_8bit: true``
     - Large models that need quantization for memory
   * - ``use_sequential_cpu_offload: true``
     - Models that need aggressive memory optimization
   * - ``enable_debug_logging: true``
     - During development, for verbose output
   * - ``supports_negative_prompt: true``
     - Models that accept negative prompts (needs CFG > 0)
   * - ``scheduler: "EulerDiscreteScheduler"``
     - Override the default scheduler
