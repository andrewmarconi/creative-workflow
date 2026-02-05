"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Language, LLMModel


@admin.register(LLMModel)
class LLMModelAdmin(ModelAdmin):
    list_display = ["name", "model_id", "show_active", "show_language_count", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "model_id", "notes"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            _("Model"),
            {
                "classes": ["tab"],
                "fields": ("model_id", "name", "is_active"),
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


@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = [
        "name",
        "code",
        "primary_model",
        "show_alternatives_count",
        "show_active",
        "updated_at",
    ]
    list_filter = ["is_active", "primary_model"]
    search_fields = ["name", "code", "notes"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["alternative_models"]
    autocomplete_fields = ["primary_model"]

    fieldsets = (
        (
            _("Language"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "is_active"),
            },
        ),
        (
            _("Models"),
            {
                "classes": ["tab"],
                "fields": ("primary_model", "alternative_models"),
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

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active

    @display(description=_("Alternatives"))
    def show_alternatives_count(self, obj):
        count = obj.alternative_models.count()
        return str(count)
