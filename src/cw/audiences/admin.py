"""Django admin configuration for audience segmentation models."""

from collections import defaultdict

from django.contrib import admin
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.sections import TableSection

from cw.core.widgets import InsightsEditorWidget

from .forms import PersonaAdminForm
from .models import (
    Country,
    CountryLanguage,
    CountryRegion,
    Language,
    LanguageAlternativeModel,
    Persona,
    PersonaSegment,
    Region,
    Segment,
    WVSProfile,
)


class InsightsWidgetMixin:
    """Mixin that replaces the insights JSONField with the structured editor."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "insights":
            kwargs["widget"] = InsightsEditorWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# Inlines for M2M relationships


class LanguageAlternativeModelInline(TabularInline):
    """Inline for managing alternative LLM models for a language."""

    model = LanguageAlternativeModel
    extra = 1
    autocomplete_fields = ["llmmodel"]
    verbose_name = "Alternative Model"
    verbose_name_plural = "Alternative Models"


class CountryRegionInline(TabularInline):
    """Inline for managing country-region relationships."""

    model = CountryRegion
    extra = 1
    autocomplete_fields = ["country"]
    verbose_name = "Country in Region"
    verbose_name_plural = "Countries in Region"


class CountryLanguageInline(TabularInline):
    """Inline for managing country-language relationships."""

    model = CountryLanguage
    extra = 1
    autocomplete_fields = ["language"]
    verbose_name = "Language"
    verbose_name_plural = "Languages"


class PersonaSegmentInline(TabularInline):
    """Inline for managing persona-segment relationships.

    NOTE: This inline is kept for reference but not used in PersonaAdmin.
    PersonaAdmin uses the custom segment builder instead.
    """

    model = PersonaSegment
    extra = 1
    autocomplete_fields = ["segment"]
    verbose_name = "Segment"
    verbose_name_plural = "Segments"
    fields = ["segment"]


# Unfold Sections


class PersonaSegmentsSection(TableSection):
    """Expandable section displaying persona segments in a table."""

    verbose_name = _("Segments")
    related_name = "personasegment_set"
    fields = ["segment_category", "segment_vector", "segment_value", "segment_description"]

    def segment_category(self, instance):
        """Display segment category with color badge."""
        category = instance.segment.category
        category_label = instance.segment.get_category_display()

        colors = {
            "DEMOGRAPHIC": "#3b82f6",
            "BEHAVIORAL": "#10b981",
            "PSYCHOGRAPHIC": "#8b5cf6",
        }
        color = colors.get(category, "#6b7280")

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500; text-transform: uppercase;">{}</span>',
            color,
            category_label,
        )

    segment_category.short_description = "Category"

    def segment_vector(self, instance):
        """Display segment vector."""
        return instance.segment.vector

    segment_vector.short_description = "Vector"

    def segment_value(self, instance):
        """Display segment value."""
        return instance.segment.value

    segment_value.short_description = "Value"

    def segment_description(self, instance):
        """Display segment description."""
        return instance.segment.description or "—"

    segment_description.short_description = "Description"


# Geographic Models Admin


@admin.register(Language)
class LanguageAdmin(InsightsWidgetMixin, ModelAdmin):
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
class RegionAdmin(InsightsWidgetMixin, ModelAdmin):
    list_display = ["name", "code", "show_countries_count", "show_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CountryRegionInline]

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


@admin.register(Country)
class CountryAdmin(InsightsWidgetMixin, ModelAdmin):
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


# Persona & Segment Admin


@admin.register(Segment)
class SegmentAdmin(InsightsWidgetMixin, ModelAdmin):
    list_display = [
        "show_category_badge",
        "vector",
        "value",
        "show_has_insights",
        "show_active",
        "updated_at",
    ]
    list_filter = ["category", "is_active", "vector"]
    search_fields = ["vector", "value", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            _("Segment"),
            {
                "classes": ["tab"],
                "fields": ("category", "vector", "value", "description", "is_active"),
            },
        ),
        (
            _("Insights"),
            {
                "classes": ["tab"],
                "fields": ("insights",),
                "description": "Structured insights for this segment",
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

    @display(description=_("Category"))
    def show_category_badge(self, obj):
        colors = {
            "DEMOGRAPHIC": "#3b82f6",  # Blue
            "BEHAVIORAL": "#10b981",  # Green
            "PSYCHOGRAPHIC": "#8b5cf6",  # Purple
        }
        color = colors.get(obj.category, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_category_display(),
        )

    @display(description=_("Has Insights"), boolean=True)
    def show_has_insights(self, obj):
        return bool(obj.insights)

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active


@admin.register(Persona)
class PersonaAdmin(ModelAdmin):
    form = PersonaAdminForm
    list_display = [
        "name",
        "show_region",
        "show_country",
        "show_language",
        "show_segment_count",
        "show_active",
        "updated_at",
    ]
    list_filter = ["is_active", "region", "country", "language"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at", "segment_builder_display"]
    autocomplete_fields = ["region", "country", "language"]
    list_sections = [PersonaSegmentsSection]

    fieldsets = (
        (
            _("Identity"),
            {
                "classes": ["tab"],
                "fields": ("name", "description", "is_active"),
            },
        ),
        (
            _("Geographic"),
            {
                "classes": ["tab"],
                "fields": ("region", "country", "language"),
                "description": "Geographic dimensions of this persona",
            },
        ),
        (
            _("Segments"),
            {
                "classes": ["tab"],
                "fields": ("segment_builder_display",),
                "description": "Build your persona by selecting demographic, behavioral, and psychographic segments.",
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

    def segment_builder_display(self, obj):
        """Render the segment builder widget as a readonly field."""
        # Get existing segments for this persona
        existing_segments = []
        if obj and obj.pk:
            existing_segments = list(
                PersonaSegment.objects.filter(persona=obj)
                .select_related("segment")
                .order_by("segment__category", "segment__vector", "segment__value")
            )

        context = {
            "categories": Segment.CATEGORY_CHOICES,
            "existing_segments": existing_segments,
            "persona_id": obj.pk if obj else None,
            "ajax_vectors_url": reverse("audiences:segment_vectors"),
            "ajax_values_url": reverse("audiences:segment_values"),
            "widget": {"attrs": {"id": "segment-builder"}},
        }

        return mark_safe(
            render_to_string("audiences/admin/segment_builder.html", context)
        )

    segment_builder_display.short_description = "Segments"

    @display(description=_("Region"))
    def show_region(self, obj):
        return obj.region.name if obj.region else "—"

    @display(description=_("Country"))
    def show_country(self, obj):
        return obj.country.name if obj.country else "—"

    @display(description=_("Language"))
    def show_language(self, obj):
        return obj.language.name if obj.language else "—"

    @display(description=_("Segments"))
    def show_segment_count(self, obj):
        count = obj.segments.count()
        if count > 0:
            return format_html("{} segments", count)
        return "No segments"

    @display(description=_("Active"), boolean=True)
    def show_active(self, obj):
        return obj.is_active


@admin.register(WVSProfile)
class WVSProfileAdmin(ModelAdmin):
    list_display = [
        "country",
        "wave",
        "show_variable_count",
        "show_view_data_link",
        "updated_at",
    ]
    list_filter = ["wave"]
    search_fields = ["country__name", "country__code"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["country"]

    fieldsets = (
        (
            _("Profile"),
            {
                "classes": ["tab"],
                "fields": ("country", "wave"),
            },
        ),
        (
            _("Raw Data"),
            {
                "classes": ["tab"],
                "fields": ("raw_data",),
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

    @display(description=_("Variables"))
    def show_variable_count(self, obj):
        return str(obj.variable_count)

    @display(description=_("View"))
    def show_view_data_link(self, obj):
        url = reverse("admin:audiences_wvsprofile_view_data", args=[obj.pk])
        return format_html(
            '<a href="{}" style="white-space: nowrap;">View Data</a>',
            url,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/view-data/",
                self.admin_site.admin_view(self.view_data),
                name="audiences_wvsprofile_view_data",
            ),
        ]
        return custom_urls + urls

    def view_data(self, request, object_id):
        """Read-only formatted view of WVS raw data grouped by theme."""
        from cw.lib.wvs import load_codebook

        profile = WVSProfile.objects.select_related("country").get(pk=object_id)
        codebook = load_codebook()

        # Group variables by theme, excluding _Sd (standard deviation) columns
        themed: dict[str, list] = defaultdict(list)
        for var_code, value in sorted(profile.raw_data.items()):
            if var_code.endswith("_Sd") or var_code.endswith("_CO_Sd"):
                continue
            entry = codebook.get(var_code, {})
            theme = entry.get("theme", "Other / Computed Indices") or "Other / Computed Indices"
            label = entry.get("label", "") or var_code
            scale = entry.get("scale", "")
            themed[theme].append({
                "code": var_code,
                "label": label,
                "value": value,
                "scale": scale,
            })

        # Sort themes: named themes first alphabetically, "Other" last
        sorted_themes = []
        other_theme = None
        for theme in sorted(themed.keys()):
            if theme == "Other / Computed Indices":
                other_theme = (theme, themed[theme])
            else:
                sorted_themes.append((theme, themed[theme]))
        if other_theme:
            sorted_themes.append(other_theme)

        # Count non-null variables
        total_vars = sum(len(vs) for _, vs in sorted_themes)
        non_null_vars = sum(
            1 for _, vs in sorted_themes for v in vs if v["value"] is not None
        )

        context = {
            **self.admin_site.each_context(request),
            "title": f"WVS Profile: {profile.country.name} — Wave {profile.wave}",
            "profile": profile,
            "themed_data": sorted_themes,
            "total_vars": total_vars,
            "non_null_vars": non_null_vars,
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request,
            "admin/audiences/wvsprofile/view_data.html",
            context,
        )
