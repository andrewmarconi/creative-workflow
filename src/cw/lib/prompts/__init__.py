"""
Jinja2 template loader for LLM prompts.

This module provides a simple interface to load and render prompt templates
from the prompts directory. By extracting prompts to external template files,
developers can easily edit, review, and version control prompt content
separately from Python code.

Template Directory Structure::

    src/cw/lib/prompts/
    ├── __init__.py              # This module (template loader)
    ├── prompt_enhancer_system.j2  # System prompt for HF/Anthropic enhancers
    ├── prompt_enhancer_user.j2    # User prompt for enhancement requests
    └── adaptation.j2              # Cultural adaptation prompt

Usage::

    from cw.lib.prompts import render_prompt

    # Render a template with variables
    prompt = render_prompt(
        "adaptation.j2",
        target_market_name="US Hispanic",
        target_market_rules="...",
        original_json=original_data,
    )

Functions:
    :func:`render_prompt`
        Render a template with the given context variables

    :func:`get_template`
        Get a raw Jinja2 template object for advanced use
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Templates directory (same directory as this module)
PROMPTS_DIR = Path(__file__).parent

# Jinja2 environment configured for text prompts (not HTML)
_env = Environment(
    loader=FileSystemLoader(PROMPTS_DIR),
    autoescape=select_autoescape([]),  # No autoescape for text prompts
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_name: str, **context: Any) -> str:
    """
    Render a prompt template with the given context.

    Args:
        template_name: Name of the template file (e.g., "adaptation.j2")
        **context: Variables to pass to the template

    Returns:
        Rendered prompt string

    Example::

        prompt = render_prompt(
            "prompt_enhancer_system.j2",
            style="photography",
            creativity=0.7,
            trigger_words="DSLR photo",
        )
    """
    template = _env.get_template(template_name)
    return template.render(**context)


def get_template(template_name: str):
    """
    Get a template object for manual rendering.

    Useful when you need to render the same template multiple times
    with different contexts.

    Args:
        template_name: Name of the template file

    Returns:
        Jinja2 Template object

    Example::

        template = get_template("adaptation.j2")
        for market in markets:
            prompt = template.render(target_market=market, ...)
    """
    return _env.get_template(template_name)
