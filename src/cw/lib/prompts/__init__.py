"""
Jinja2 template loader for LLM prompts.

Templates are loaded exclusively from the database (PromptTemplate model).
This enables live editing via Django admin without code deployment.
Results are cached in Redis/memory for 5 minutes to minimize DB hits.

Usage::

    from cw.lib.prompts import render_prompt

    prompt = render_prompt(
        "adaptation",
        target_market_name="US Hispanic",
        target_market_rules="...",
        original_json=original_data,
    )
"""

import logging
from typing import Any

from django.core.cache import cache
from django.db import models
from django.utils import timezone
from jinja2 import Environment

logger = logging.getLogger(__name__)

# Shared Jinja2 environment for rendering from DB content
_env = Environment(trim_blocks=True, lstrip_blocks=True)


def render_prompt(slug: str, **context: Any) -> str:
    """
    Render a prompt template with the given context.

    Loads the template from the database (PromptTemplate model) by slug,
    with Redis/memory caching (5-minute TTL) and usage analytics.

    Args:
        slug: Template slug (e.g., "adaptation", "eval-brand")
        **context: Variables to pass to the template

    Returns:
        Rendered prompt string

    Raises:
        PromptTemplate.DoesNotExist: If no active template with the given slug exists

    Example::

        prompt = render_prompt(
            "adaptation",
            target_market_name="US Hispanic",
            original_json=data,
        )
    """
    # Check cache first
    cache_key = f"prompt_template:{slug}"
    cached_content = cache.get(cache_key)

    if cached_content is not None:
        template = _env.from_string(cached_content)
        return template.render(**context)

    # Cache miss — load from database
    from cw.core.models import PromptTemplate

    prompt_obj = PromptTemplate.objects.get(slug=slug, is_active=True)
    template_content = prompt_obj.template

    # Update usage analytics
    PromptTemplate.objects.filter(pk=prompt_obj.pk).update(
        usage_count=models.F("usage_count") + 1, last_used_at=timezone.now()
    )

    # Cache for 5 minutes
    cache.set(cache_key, template_content, timeout=300)

    template = _env.from_string(template_content)
    return template.render(**context)
