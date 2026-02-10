Contributing
============

How to contribute to the project. This consolidates the root ``CONTRIBUTING.md`` into the documentation.

Development Setup
-----------------

Prerequisites
^^^^^^^^^^^^^

- **Python 3.12+**
- **uv** --- fast Python package manager
- **Docker** --- for PostgreSQL and Valkey containers
- **Git**

Initial Setup
^^^^^^^^^^^^^

.. code-block:: bash

   # 1. Clone the repository
   git clone git@github.com:andrewmarconi/generative-creative-lab.git
   cd generative-creative-lab

   # 2. Install dependencies
   uv sync

   # 3. Configure environment
   cp .env.example .env   # Edit with your settings

   # 4. Start services
   ./start.sh             # Waits for containers to be healthy

   # 5. Set up the database
   uv run manage.py migrate
   uv run manage.py import_reference_data
   uv run manage.py import_prompt_templates
   uv run manage.py import_presets
   uv run manage.py createsuperuser

   # 6. Access the application
   # Django admin: http://localhost:8000/admin
   # Flower:       http://localhost:5555
   # Grafana:      http://localhost:3000

Code Style
----------

Python
^^^^^^

- Follow **PEP 8** conventions
- Use **Google-style docstrings** for all public functions, classes, and modules
- Keep lines under **100 characters** where practical
- Use **type hints** for function parameters and return values

Import Ordering
^^^^^^^^^^^^^^^

Organize imports in four groups, separated by blank lines:

1. Standard library
2. Third-party packages
3. Django
4. Local application

.. code-block:: python

   import os
   from typing import Dict, Optional

   import torch
   from diffusers import DiffusionPipeline

   from django.db import models

   from cw.lib.config import PresetsConfig
   from cw.lib.models.base import BaseModel

Docstrings
^^^^^^^^^^

Use Google-style format:

.. code-block:: python

   def generate_image(prompt: str, steps: int = 30) -> str:
       """Generate an image from a text prompt.

       Args:
           prompt: The text description of the image to generate.
           steps: Number of diffusion steps. Defaults to 30.

       Returns:
           Path to the generated image file.

       Raises:
           ValueError: If prompt is empty or steps is negative.
       """

Making Changes
--------------

Branch Naming
^^^^^^^^^^^^^

Create branches from ``develop`` with descriptive prefixes:

- ``feature/`` --- new features (e.g., ``feature/add-flux2-model``)
- ``fix/`` --- bug fixes (e.g., ``fix/lora-loading-error``)
- ``docs/`` --- documentation (e.g., ``docs/update-api-reference``)
- ``refactor/`` --- code restructuring (e.g., ``refactor/simplify-pipeline``)
- ``test/`` --- test improvements (e.g., ``test/add-model-tests``)

Commit Messages
^^^^^^^^^^^^^^^

Write clear, present-tense messages:

.. code-block:: text

   Add Flux 2.5 model support

   Implement Flux 2.5 model with updated pipeline configuration
   and 8-bit quantization support. Closes #42

Testing
^^^^^^^

- Write tests for new features and bug fixes
- Run existing tests before submitting: ``uv run python test_admin.py``
- Test manually in the admin interface where applicable

Building Documentation
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   cd docs && make html
   # View at docs/_build/html/index.html

   # Clean and rebuild
   cd docs && make clean && make html

Pull Request Process
--------------------

Before Submitting
^^^^^^^^^^^^^^^^^

- Code follows project style guidelines
- All tests pass locally
- Documentation is updated (if applicable)
- Branch is up to date with ``develop``

PR Format
^^^^^^^^^

.. code-block:: text

   ## Summary
   Brief description of what this PR does.

   ## Changes
   - Bullet list of specific changes

   ## Related Issues
   Fixes #123

   ## Testing
   How to test these changes.

Review Process
^^^^^^^^^^^^^^

1. Automated checks run tests and linting
2. Maintainers review the code
3. Address any requested changes
4. At least one maintainer approval required
5. Maintainer merges once approved

Issue Guidelines
----------------

Bug Reports
^^^^^^^^^^^

Include: description, steps to reproduce, expected vs. actual behavior, environment details, error messages.

Feature Requests
^^^^^^^^^^^^^^^^

Include: description, use case, proposed solution, alternatives considered.

Code of Conduct
---------------

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Provide constructive feedback
- Focus on what is best for the community

License
-------

By contributing, you agree that your contributions will be licensed under the same license as the project.
