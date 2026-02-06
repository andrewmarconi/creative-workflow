JSON Data Schemas
=================

JSON Schema definitions for the data files used by Generative Creative Lab. All schemas
use `JSON Schema draft 2020-12 <https://json-schema.org/draft/2020-12/schema>`_.

These files are used for moving information into or out of the platform.

----

Presets Schema
--------------

Defines the configuration for diffusion models and LoRA adapters.

:Data File: :download:`presets.json <../../data/presets.json>`
:Schema: :download:`presets.schema.json <../../data/presets.schema.json>`

Structure
~~~~~~~~~

The presets file contains two top-level arrays:

**models**
   Available diffusion models with their pipeline configurations and inference settings.

**loras**
   LoRA adapters with CivitAI AIR URNs for auto-download and recommended settings.

Model Properties
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``slug``
     - string
     - Unique identifier (lowercase, underscores only)
   * - ``label``
     - string
     - Human-readable display name
   * - ``path``
     - string
     - HuggingFace model path or local ``.safetensors`` path
   * - ``pipeline``
     - string
     - Diffusers pipeline class name
   * - ``base_architecture``
     - string
     - Base model architecture: ``sd15``, ``sdxl``, ``flux1``, ``qwen``, ``zimage``
   * - ``settings``
     - object
     - Inference settings (steps, guidance, dimensions, etc.)

LoRA Properties
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``label``
     - string
     - Human-readable display name
   * - ``base_architecture``
     - string
     - Compatible base model architecture
   * - ``theme``
     - string
     - Visual style category for filtering
   * - ``air``
     - string
     - CivitAI AIR URN for auto-download
   * - ``prompt``
     - string
     - Trigger words to append when using this LoRA
   * - ``negative_prompt``
     - string
     - Recommended negative prompt
   * - ``settings.strength``
     - number
     - LoRA weight multiplier (0-2)

Example
~~~~~~~

.. code-block:: json

   {
     "models": [
       {
         "slug": "flux1_dev",
         "label": "Flux.1 Dev",
         "path": "black-forest-labs/FLUX.1-dev",
         "pipeline": "FluxPipeline",
         "base_architecture": "flux1",
         "settings": {
           "steps": 28,
           "guidance_scale": 3.5,
           "default_width": 1024,
           "default_height": 1024,
           "max_pixels": 2097152,
           "dtype": "bfloat16",
           "supports_negative_prompt": false,
           "scheduler": "FlowMatchEulerDiscreteScheduler",
           "max_sequence_length": 512,
           "token_window": 512,
           "vram_usage": 24576
         }
       }
     ],
     "loras": [
       {
         "label": "Pen & Ink Illustration",
         "base_architecture": "zimage",
         "theme": "illustration",
         "settings": {
           "strength": 0.7,
           "guidance_scale": 1.0
         },
         "air": "urn:air:zimageturbo:lora:civitai:2344335@2636956",
         "prompt": "phrsink, pen and ink illustration"
       }
     ]
   }

----

TV Spot Schema
--------------

Defines the format for television commercial scripts used in adaptation workflows.

:Data File: :download:`example_tvspot.json <../../data/example_tvspot.json>`
:Schema: :download:`tvspot.schema.json <../../data/tvspot.schema.json>`

Structure
~~~~~~~~~

A TV spot script contains metadata about the commercial and a sequential array of shots.

Top-Level Properties
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``client_name``
     - string
     - Name of the client or company
   * - ``brand_name``
     - string
     - Product or brand featured in the spot
   * - ``script_title``
     - string
     - Title with duration indicator (e.g., "Morning Boost 30s")
   * - ``total_runtime_seconds``
     - number
     - Total duration in seconds
   * - ``job_id``
     - string
     - Internal project identifier
   * - ``language``
     - string
     - BCP 47 language code (e.g., ``en-US``, ``es-MX``)
   * - ``notes``
     - string
     - Additional production notes
   * - ``script_rows``
     - array
     - Sequential shots/scenes

Script Row Properties
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Property
     - Type
     - Description
   * - ``shot_number``
     - string
     - Two-digit shot identifier (e.g., ``"01"``)
   * - ``timecode_start``
     - string
     - Start timecode in ``HH:MM:SS:FF`` format
   * - ``duration_seconds``
     - number
     - Duration of the shot in seconds
   * - ``visual_text``
     - string
     - Visual description: shot type, action, talent, supers, legal
   * - ``audio_text``
     - string
     - Audio elements: VO, SFX, music direction

Example
~~~~~~~

.. code-block:: json

   {
     "client_name": "Acme Corporation",
     "brand_name": "Acme Energy Drink",
     "script_title": "Morning Boost 30s",
     "total_runtime_seconds": 30,
     "job_id": "ACME-2024-001",
     "language": "en-US",
     "script_rows": [
       {
         "shot_number": "01",
         "timecode_start": "00:00:00:00",
         "duration_seconds": 3.0,
         "visual_text": "Wide shot: Urban apartment, early morning...",
         "audio_text": "SFX: Alarm buzzing\nMUSIC: Soft, building instrumental"
       }
     ]
   }

----

Market Profiles Schema
----------------------

Defines linguistic-cultural market zones for television commercial adaptation.

:Data File: :download:`market_profiles.json <../../data/market_profiles.json>`
:Schema: :download:`market_profiles.schema.json <../../data/market_profiles.schema.json>`

See :doc:`/research/AdaptationProfiles` for detailed documentation of the market profiles framework.

Structure
~~~~~~~~~

The market profiles file contains an array of markets and methodology notes.

Market Properties
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``name``
     - string
     - Full name of the market zone
   * - ``code``
     - string
     - Short identifier (e.g., ``fr``, ``de``, ``zh-cn``, ``us-hispanic``)
   * - ``primary_regions``
     - array
     - Countries or regions covered by this profile
   * - ``secondary_reach``
     - array
     - Secondary regions where profile may apply
   * - ``rules``
     - array
     - Adaptation guidelines organized by category

Rule Category Properties
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Property
     - Type
     - Description
   * - ``heading``
     - string
     - Category name (e.g., "Language segmentation", "Cultural considerations")
   * - ``points``
     - array
     - Individual guidance points within this category

Example
~~~~~~~

.. code-block:: json

   {
     "markets": [
       {
         "name": "French Language Zone",
         "code": "fr",
         "primary_regions": ["France", "Belgium (Wallonia/Brussels)", "Luxembourg"],
         "secondary_reach": ["Quebec (Canada)", "Francophone Africa"],
         "rules": [
           {
             "heading": "Language segmentation",
             "points": [
               "Belgium requires two distinct versions: Dutch for Flanders and French for Wallonia.",
               "Quebec Canadian French has distinct vocabulary and cultural references."
             ]
           }
         ]
       }
     ],
     "methodology_notes": {
       "approach": "This framework prioritizes linguistic-cultural zones...",
       "anthropological_principles": ["..."],
       "avoiding_stereotypes": ["..."]
     }
   }
