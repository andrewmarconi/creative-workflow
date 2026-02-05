Adding New Models
=================

This guide covers how to add new diffusion models to Creative Workflow.

Model Architecture
------------------

Creative Workflow uses a **Template Method Pattern** for model implementations:

- **BaseModel** (``cw.lib.models.base``) - Abstract base with concrete template methods
- **Mixins** (``cw.lib.models.mixins``) - Shared behaviors via multiple inheritance
- **Concrete Models** - Minimal implementations (20-70 lines each)

Adding a Simple Model
---------------------

Most models only need to override ``_create_pipeline()``:

.. code-block:: python

    # src/cw/lib/models/newmodel.py
    from diffusers import YourPipeline
    from .base import BaseModel

    class YourModel(BaseModel):
        def _create_pipeline(self):
            return YourPipeline.from_pretrained(
                self.model_path,
                torch_dtype=self.dtype,
            )

Then register it in ``cw/lib/models/__init__.py``:

.. code-block:: python

    from .newmodel import YourModel

    # Add to ModelFactory.create_model()

Adding Model Configuration
--------------------------

Add the model to ``data/presets.json``:

.. code-block:: json

    {
        "models": [
            {
                "label": "Your Model Name",
                "slug": "your-model",
                "path": "Huggingface:org/model-id",
                "pipeline": "your_pipeline_type",
                "settings": {
                    "steps": 30,
                    "guidance_scale": 7.0,
                    "default_width": 1024,
                    "default_height": 1024,
                    "scheduler": "euler_a",
                    "dtype": "bfloat16",
                    "supports_negative_prompt": true
                }
            }
        ]
    }

Then sync to database::

    uv run manage.py import_presets

Models with Special Requirements
--------------------------------

**Long prompts + prompt weighting** (CLIP-based models):

.. code-block:: python

    from .base import BaseModel
    from .mixins import CompelPromptMixin

    class YourSDXLModel(CompelPromptMixin, BaseModel):
        def _create_pipeline(self):
            # CompelPromptMixin handles >77 tokens and (word:weight) syntax
            ...

**Custom prompt handling**:

.. code-block:: python

    class YourModel(BaseModel):
        def _build_prompts(self, params):
            # Custom prompt processing
            return {"prompt": processed_prompt}

**Custom pipeline kwargs**:

.. code-block:: python

    class YourModel(BaseModel):
        def _build_pipeline_kwargs(self, params, callback):
            kwargs = super()._build_pipeline_kwargs(params, callback)
            kwargs["custom_param"] = value
            return kwargs

Configuration Flags
-------------------

Available flags in ``settings`` (presets.json):

- ``force_default_guidance`` - Force default guidance_scale (Turbo models)
- ``enable_debug_logging`` - Enable debug print statements
- ``use_sequential_cpu_offload`` - Use sequential vs model CPU offload
- ``max_sequence_length`` - Context length for Flux variants
- ``load_in_8bit`` - 8-bit quantization

Path Resolution
---------------

- **HuggingFace**: ``Huggingface:org/model-id`` - loaded via ``from_pretrained()``
- **Local**: ``path/to/model.safetensors`` - loaded via ``from_single_file()``
