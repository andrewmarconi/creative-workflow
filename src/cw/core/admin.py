"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import LLMModel


@admin.register(LLMModel)
class LLMModelAdmin(ModelAdmin):
    list_display = ["name", "model_id", "show_4bit", "show_active", "show_language_count", "updated_at"]
    list_filter = ["is_active", "load_in_4bit"]
    search_fields = ["name", "model_id", "notes"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            _("Model"),
            {
                "classes": ["tab"],
                "fields": ("model_id", "name", ("is_active", "load_in_4bit")),
            },
        ),
        (
            _("Notes"),
            {
                "classes": ["tab"],
                "fields": ("notes",),
            },
        ),
        (
            _("Metadata"),
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(description=_("4-bit"), boolean=True)
    def show_4bit(self, obj):
        return obj.load_in_4bit

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("Languages"))
    def show_language_count(self, obj):
        # Count languages where this is primary or alternative
        primary_count = obj.primary_for_languages.count()
        alt_count = obj.alternative_for_languages.count()
        total = primary_count + alt_count
        if total > 0:
            return format_html(
                "{} <small>({} primary, {} alt)</small>",
                total,
                primary_count,
                alt_count,
            )
        return "0"
