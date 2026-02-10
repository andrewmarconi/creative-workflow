Prompt Template Editing
=======================

This guide covers editing the LLM prompts used by the adaptation pipeline and prompt enhancement system.

Overview
--------

All LLM prompts are stored in the ``PromptTemplate`` model — database-only, with no filesystem fallback. This enables live editing via the Django admin without code deployment.

Templates use **Jinja2** syntax, support **versioning** (one active version per slug), and include **usage analytics** (render count and last-used timestamp).

Editing a Template
------------------

1. Navigate to **Core > Prompt Templates**
2. Select the template to edit
3. Modify the **Template** field (Jinja2 syntax)
4. Save — this automatically:

   - Creates a new version (auto-incremented)
   - Deactivates the previous version
   - Invalidates the cache (changes take effect within 5 minutes)

5. No deployment needed — changes are live immediately

Template Categories
-------------------

Nine templates organized into four categories:

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Slug
     - Category
     - Purpose
   * - ``prompt-enhancer-system``
     - Enhancement
     - System prompt for HF/Anthropic prompt enhancers
   * - ``prompt-enhancer-user``
     - Enhancement
     - User prompt for enhancement requests
   * - ``adaptation``
     - Adaptation
     - Main TV spot cultural adaptation (script writing)
   * - ``concept-extraction``
     - Concept
     - Analyzes original script for core concept
   * - ``cultural-research``
     - Concept
     - Produces cultural brief for target market
   * - ``eval-format``
     - Evaluation
     - Evaluates language compliance
   * - ``eval-cultural``
     - Evaluation
     - Evaluates cultural appropriateness
   * - ``eval-concept``
     - Evaluation
     - Evaluates concept fidelity
   * - ``eval-brand``
     - Evaluation
     - Evaluates brand consistency

Jinja2 Syntax
-------------

Templates use Jinja2 with ``trim_blocks`` and ``lstrip_blocks`` enabled:

.. code-block:: jinja

   You are adapting a TV commercial for {{ target_market_name }}.

   ## Original Script
   {{ original_json }}

   {% if brand_guidelines %}
   ## Brand Guidelines
   {{ brand_guidelines }}
   {% endif %}

   ## Instructions
   Adapt the script for the target market while preserving the core concept.

Variables are passed as keyword arguments to ``render_prompt()``:

.. code-block:: python

   from cw.lib.prompts import render_prompt

   prompt = render_prompt(
       "adaptation",
       target_market_name="Germany",
       original_json=script_data,
       brand_guidelines=brand.guidelines,
   )

Jinja2 syntax is **validated on save** — if the template contains invalid syntax, a ``ValidationError`` is raised and the save is rejected.

Template Variables
------------------

Each template declares its expected variables in the ``expected_variables`` JSON field:

.. code-block:: json

   {
     "target_market_name": {
       "type": "string",
       "required": true,
       "description": "Name of the target market (e.g., 'Germany')"
     },
     "original_json": {
       "type": "string",
       "required": true,
       "description": "Original script as JSON string"
     }
   }

This field is informational — it documents what variables the template expects but does not enforce them at render time.

Versioning
----------

Every edit creates a new version:

- **Version number** — auto-incremented per slug
- **Active flag** — only one version per slug can be active at a time
- **Previous versions** — retained for audit trail and rollback

To roll back to a previous version:

1. Find the previous version in the template list (filter by slug)
2. Set its ``is_active`` flag to ``True``
3. Save — the current version is automatically deactivated

Cache Invalidation
------------------

Rendered templates are cached with a 5-minute TTL:

- **Cache key**: ``prompt_template:{slug}``
- **Backend**: Django cache (Redis or memory)
- **TTL**: 300 seconds

After editing a template, changes take effect within 5 minutes as cached entries expire. For immediate effect, clear the cache manually or restart the worker.

Usage Analytics
---------------

Each template tracks:

- ``usage_count`` — number of times rendered (incremented atomically via ``F()`` expression)
- ``last_used_at`` — timestamp of the most recent render

These fields are visible on the template detail page and help identify which templates are actively used.

Import & Export
---------------

.. code-block:: bash

   # Import templates from data/prompt_templates.json
   uv run manage.py import_prompt_templates

   # Preview without importing
   uv run manage.py import_prompt_templates --dry-run

   # Export active templates to data/prompt_templates.json
   uv run manage.py export_prompt_templates

   # Export to a custom directory
   uv run manage.py export_prompt_templates --dir custom/

The ``data/prompt_templates.json`` file is the source of truth for bootstrapping new environments.
