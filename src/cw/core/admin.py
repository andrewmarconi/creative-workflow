"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import (
    Country,
    CountryLanguage,
    CountryRegion,
    Culture,
    Language,
    LanguageAlternativeModel,
    LLMModel,
    Region,
    RegionCulture,
)


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


class LanguageAlternativeModelInline(admin.TabularInline):
    """Inline for managing alternative LLM models for a language."""

    model = LanguageAlternativeModel
    extra = 1
    autocomplete_fields = ["llmmodel"]
    verbose_name = "Alternative Model"
    verbose_name_plural = "Alternative Models"


class CountryRegionInline(admin.TabularInline):
    """Inline for managing country-region relationships."""

    model = CountryRegion
    extra = 1
    autocomplete_fields = ["country"]
    verbose_name = "Country in Region"
    verbose_name_plural = "Countries in Region"


class CountryLanguageInline(admin.TabularInline):
    """Inline for managing country-language relationships."""

    model = CountryLanguage
    extra = 1
    autocomplete_fields = ["language"]
    verbose_name = "Language"
    verbose_name_plural = "Languages"


class RegionCultureInline(admin.TabularInline):
    """Inline for managing region-culture relationships."""

    model = RegionCulture
    extra = 1
    autocomplete_fields = ["culture"]
    verbose_name = "Culture"
    verbose_name_plural = "Cultures"


@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = [
        "name",
        "code",
        "base_language",
        "primary_model",
        "show_alternatives_count",
        "show_active",
        "updated_at",
    ]
    list_filter = ["is_active", "base_language", "primary_model"]
    search_fields = ["name", "code", "base_language", "notes"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["primary_model"]
    inlines = [LanguageAlternativeModelInline]

    fieldsets = (
        (
            _("Language"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "base_language", "is_active"),
            },
        ),
        (
            _("Models"),
            {
                "classes": ["tab"],
                "fields": ("primary_model",),
            },
        ),
        (
            _("Insights"),
            {
                "classes": ["tab"],
                "fields": ("insights",),
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


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ["name", "code", "show_countries_count", "show_cultures_count", "show_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CountryRegionInline, RegionCultureInline]

    fieldsets = (
        (
            _("Region"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "description", "is_active"),
            },
        ),
        (
            _("Insights"),
            {
                "classes": ["tab"],
                "fields": ("insights",),
                "description": "Cultural patterns and characteristics for this region",
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

    @display(description=_("Countries"))
    def show_countries_count(self, obj):
        count = obj.countries.count()
        return str(count)

    @display(description=_("Cultures"))
    def show_cultures_count(self, obj):
        count = obj.cultures.count()
        return str(count)


@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = [
        "name",
        "code",
        "default_language",
        "show_regions_count",
        "show_languages_count",
        "show_active",
        "updated_at",
    ]
    list_filter = ["is_active", "default_language"]
    search_fields = ["name", "code", "notes"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["default_language"]
    inlines = [CountryLanguageInline]

    fieldsets = (
        (
            _("Country"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "default_language", "is_active"),
            },
        ),
        (
            _("Insights"),
            {
                "classes": ["tab"],
                "fields": ("insights",),
                "description": "Country-specific regulatory and cultural rules",
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

    @display(description=_("Regions"))
    def show_regions_count(self, obj):
        count = obj.regions.count()
        return str(count)

    @display(description=_("Languages"))
    def show_languages_count(self, obj):
        count = obj.languages.count()
        return str(count)


@admin.register(Culture)
class CultureAdmin(ModelAdmin):
    list_display = ["name", "code", "show_regions_count", "show_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            _("Culture"),
            {
                "classes": ["tab"],
                "fields": ("code", "name", "description", "is_active"),
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

    @display(description=_("Regions"))
    def show_regions_count(self, obj):
        count = obj.regions.count()
        return str(count)
