"""Custom widgets for core admin forms."""

import json
from typing import Any

from django.forms import Textarea

from unfold.widgets import BASE_INPUT_CLASSES, INPUT_CLASSES


class InsightsEditorWidget(Textarea):
    """Structured editor for insights JSON fields.

    Renders an Alpine.js-powered UI for editing an array of
    {heading: str, points: str[]} objects, with a hidden textarea
    that holds the serialized JSON for form submission.
    """

    template_name = "core/widgets/insights_editor.html"

    class Media:
        js = ("core/js/insights_editor.js",)

    def __init__(self, attrs: dict[str, Any] | None = None) -> None:
        defaults = {"class": " ".join([*BASE_INPUT_CLASSES, "hidden"])}
        if attrs:
            defaults.update(attrs)
        super().__init__(attrs=defaults)

    def get_context(
        self, name: str, value: Any, attrs: dict[str, Any] | None
    ) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)

        # Parse the JSON value for the Alpine.js component
        sections = []
        if value:
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
                if isinstance(parsed, list):
                    sections = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        context["sections_json"] = json.dumps(sections)
        context["input_classes"] = " ".join(INPUT_CLASSES)

        return context
