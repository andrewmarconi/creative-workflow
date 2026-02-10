"""Custom widgets for core admin forms."""

import json
from pathlib import Path
from typing import Any

from django.conf import settings
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


class ScriptEditorWidget(Textarea):
    """Structured editor for TV spot script JSON with schema validation.

    Renders an Alpine.js-powered UI for editing script_rows following
    the tvspot.schema.json format, with real-time validation feedback.
    """

    template_name = "core/widgets/script_editor.html"

    class Media:
        js = ("core/js/script_editor.js",)

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
        script_data = {}
        if value:
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
                if isinstance(parsed, dict):
                    script_data = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # Load JSON schema for validation
        schema_path = Path(settings.BASE_DIR) / "data" / "schemas" / "tvspot.schema.json"
        schema = {}
        try:
            with open(schema_path) as f:
                schema = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        context["script_json"] = json.dumps(script_data)
        context["schema_json"] = json.dumps(schema)
        context["input_classes"] = " ".join(INPUT_CLASSES)

        return context


class VideoPlayerWidget(Textarea):
    """Video player widget with scene timeline markers.

    Displays video with interactive timeline showing scene boundaries
    and allows jumping to specific scenes.
    """

    template_name = "core/widgets/video_player.html"

    class Media:
        js = ("core/js/video_player.js",)

    def __init__(self, video_url: str | None = None, scenes: list | None = None, attrs: dict[str, Any] | None = None) -> None:
        defaults = {"class": "hidden"}
        if attrs:
            defaults.update(attrs)
        super().__init__(attrs=defaults)
        self.video_url = video_url
        self.scenes = scenes or []

    def get_context(
        self, name: str, value: Any, attrs: dict[str, Any] | None
    ) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)

        context["video_url"] = self.video_url or ""
        context["scenes_json"] = json.dumps(self.scenes)

        return context
