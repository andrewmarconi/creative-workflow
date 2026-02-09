"""
Jinja2 template loader for LLM prompts.

This module provides a unified interface to load and render prompt templates
from either the database (PromptTemplate model) or file-based fallback.

**Database-First Lookup** (with caching):
    Templates are first loaded from the PromptTemplate model in the database.
    This enables live editing via Django admin without code deployment.
    Results are cached in Redis/memory for 5 minutes to minimize DB hits.

**File-Based Fallback**:
    If a template is not found in the database, the system falls back to
    loading from `.j2` files in the prompts directory. This provides
    backward compatibility during migration.

Template Directory Structure::

    src/cw/lib/prompts/
    ├── __init__.py              # This module (template loader)
    ├── prompt_enhancer_system.j2  # System prompt for HF/Anthropic enhancers
    ├── prompt_enhancer_user.j2    # User prompt for enhancement requests
    └── adaptation.j2              # Cultural adaptation prompt

Usage::

    from cw.lib.prompts import render_prompt

    # Render a template (tries DB first, then file fallback)
    prompt = render_prompt(
        "adaptation",  # Can use slug or "adaptation.j2"
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

import logging
from pathlib import Path
from typing import Any

from django.core.cache import cache
from django.db import models
from django.utils import timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

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

    This function uses a **database-first lookup strategy** with file fallback:
    1. Normalize template name (strip .j2/.jinja2 extension)
    2. Check database (PromptTemplate) with Redis caching (5 min TTL)
    3. If not in DB, fall back to file-based loading from .j2 files
    4. Update usage analytics for DB templates

    Args:
        template_name: Template slug or filename (e.g., "adaptation" or "adaptation.j2")
        **context: Variables to pass to the template

    Returns:
        Rendered prompt string

    Example::

        # Using slug (database lookup)
        prompt = render_prompt(
            "adaptation",
            target_market_name="US Hispanic",
            original_json=data,
        )

        # Using filename (backward compatible)
        prompt = render_prompt(
            "adaptation.j2",
            target_market_name="US Hispanic",
            original_json=data,
        )
    """
    # Normalize: strip .j2/.jinja2 extension to get slug
    slug = template_name.replace(".j2", "").replace(".jinja2", "")

    # Try database first (with caching)
    cache_key = f"prompt_template:{slug}"
    cached_content = cache.get(cache_key)

    if cached_content is not None:
        # Cache hit - render directly from cached content
        env = Environment(trim_blocks=True, lstrip_blocks=True)
        template = env.from_string(cached_content)
        return template.render(**context)

    # Cache miss - try database
    try:
        from cw.core.models import PromptTemplate

        prompt_obj = PromptTemplate.objects.get(slug=slug, is_active=True)
        template_content = prompt_obj.template

        # Update usage analytics (async to avoid blocking)
        PromptTemplate.objects.filter(pk=prompt_obj.pk).update(
            usage_count=models.F("usage_count") + 1, last_used_at=timezone.now()
        )

        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, template_content, timeout=300)

        # Render from DB content
        env = Environment(trim_blocks=True, lstrip_blocks=True)
        template = env.from_string(template_content)
        return template.render(**context)

    except Exception:
        # Database lookup failed - fall back to file-based loading
        logger.debug(
            f"PromptTemplate '{slug}' not found in database, falling back to file"
        )

        # Use file-based loading with original template_name
        # (might include .j2 extension if user provided it)
        if not template_name.endswith((".j2", ".jinja2")):
            template_name = f"{template_name}.j2"

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
