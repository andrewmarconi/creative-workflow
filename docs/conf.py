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
copyright = "2026, Andrew Marconi"
author = "Andrew Marconi"
release = "0.1.0"

github_url = "https://github.com/andrewmarconi/generative-creative-lab"
html_logo = "_static/logo.png"
html_title = "Generative Creative Lab"

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

# Suppress warnings from sphinx_autodoc_typehints for decorated functions
# (Django Unfold's @action decorator doesn't use @functools.wraps)
suppress_warnings = [
    "sphinx_autodoc_typehints.local_function",
    "sphinx_autodoc_typehints.forward_reference",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

# RTD theme options
html_theme_options = {
    "navigation_depth": 4,  # Show up to 4 levels in sidebar
    "collapse_navigation": False,  # Keep navigation expanded
    "sticky_navigation": True,  # Sticky sidebar
    "includehidden": True,  # Include hidden toctrees in navigation
    "logo_only": True,  # True = hide project name, show only logo
    "style_external_links": True,  # Add icon to external links
}

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

# -- Linkcheck configuration -------------------------------------------------

linkcheck_ignore = [
    r"^urn:air:.*",  # CivitAI AIR URN identifiers (not HTTP links)
    r"^http://localhost.*",  # Local dev server links
]
