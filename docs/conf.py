"""
Sphinx configuration for Generative Creative Lab documentation.
"""

import os
import sys

import django

# Add src to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# Setup Django before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cw.settings")
django.setup()

# -- Project information -----------------------------------------------------

project = "Generative Creative Lab"
copyright = "2026"
author = "Andrew Marconi"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Google/NumPy docstrings
    "sphinx.ext.viewcode",  # Source links
    "sphinx.ext.intersphinx",  # Cross-references
    "sphinx_autodoc_typehints",  # Type hints in docs
    "myst_parser",  # Markdown support
    "sphinxcontrib.mermaid",  # Mermaid diagrams
]

# Mermaid settings
mermaid_version = "11"  # Use latest Mermaid.js

# Napoleon settings (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# -- Intersphinx mapping -----------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/6.0/",
        "https://docs.djangoproject.com/en/6.0/_objects/",
    ),
    "celery": ("https://docs.celeryq.dev/en/stable/", None),
}

# -- Source file handling ----------------------------------------------------

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "DOCUMENTATION_PLAN.md"]
