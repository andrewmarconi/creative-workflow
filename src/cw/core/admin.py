"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from django.utils import timezone

from .models import LLMModel, PipelineSettings, PromptTemplate


@admin.register(LLMModel)
class LLMModelAdmin(ModelAdmin):
    list_display = [
        "name",
        "model_id",
        "show_4bit",
        "show_active",
        "show_language_count",
        "updated_at",
    ]
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


@admin.register(PromptTemplate)
class PromptTemplateAdmin(ModelAdmin):
    """Admin interface for PromptTemplate with Unfold styling and tabs."""

    list_display = [
        "name",
        "slug",
        "category",
        "version",
        "is_active",
        "usage_count",
        "last_used_at",
        "updated_at",
    ]
    list_filter = ["category", "is_active", "created_at", "updated_at"]
    search_fields = ["name", "slug", "description", "template"]
    readonly_fields = [
        "version",
        "created_at",
        "updated_at",
        "usage_count",
        "last_used_at",
    ]

    # Unfold tabs configuration - all fieldsets are tabs
    fieldsets = (
        (
            "Overview",
            {
                "fields": ("slug", "name", "category", "is_active"),
                "classes": ("tab",),
                "description": "Basic template information and status",
            },
        ),
        (
            "Documentation",
            {
                "fields": ("description",),
                "classes": ("tab",),
                "description": "Purpose, usage notes, and examples for this template",
            },
        ),
        (
            "Template Content",
            {
                "fields": ("template",),
                "classes": ("tab",),
                "description": "Jinja2 template content - use {{ variable }} syntax for placeholders",
            },
        ),
        (
            "Variables",
            {
                "fields": ("expected_variables",),
                "classes": ("tab",),
                "description": "Expected template variables (JSON format): {name: {type, required, description}}",
            },
        ),
        (
            "Version Information",
            {
                "fields": ("version", "created_by", "created_at", "updated_at"),
                "classes": ("tab",),
                "description": "Version history and authorship information",
            },
        ),
        (
            "Usage Analytics",
            {
                "fields": ("usage_count", "last_used_at"),
                "classes": ("tab",),
                "description": "Template usage statistics and metrics",
            },
        ),
    )

    actions = ["duplicate_template", "activate_version", "test_render"]

    def duplicate_template(self, request, queryset):
        """Create draft copy for A/B testing."""
        for template in queryset:
            template.pk = None  # Force new record
            template.slug = f"{template.slug}-draft-{timezone.now().strftime('%Y%m%d')}"
            template.is_active = False
            template.version = 1
            template.created_by = request.user
            template.save()
        self.message_user(
            request,
            f"Created {queryset.count()} draft template(s)",
        )

    duplicate_template.short_description = "Duplicate selected templates as drafts"

    def activate_version(self, request, queryset):
        """Set selected version as active (deactivates other versions of same slug)."""
        for template in queryset:
            # Deactivate all other versions of this slug
            PromptTemplate.objects.filter(slug=template.slug).update(is_active=False)
            # Activate this version
            template.is_active = True
            template.save(update_fields=["is_active"])

        self.message_user(
            request,
            f"Activated {queryset.count()} template version(s)",
        )

    activate_version.short_description = "Activate selected template versions"

    def test_render(self, request, queryset):
        """Test rendering templates with sample data (basic validation)."""
        success_count = 0
        error_count = 0

        for template in queryset:
            try:
                # Test render with empty context
                template.render()
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Template '{template.name}' failed to render: {e}",
                    level="error",
                )

        if success_count:
            self.message_user(
                request,
                f"{success_count} template(s) rendered successfully",
            )

    test_render.short_description = "Test render selected templates (empty context)"

    def get_queryset(self, request):
        """Optimize queryset with select_related for created_by."""
        qs = super().get_queryset(request)
        return qs.select_related("created_by")

    def save_model(self, request, obj, form, change):
        """Set created_by to current user on creation."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PipelineSettings)
class PipelineSettingsAdmin(ModelAdmin):
    """Singleton admin for per-node LLM model defaults."""

    fieldsets = (
        (
            _("Global Default"),
            {
                "classes": ["tab"],
                "fields": ("global_default_model",),
                "description": "Fallback model used when no node-specific default is configured.",
            },
        ),
        (
            _("Research Nodes"),
            {
                "classes": ["tab"],
                "fields": ("concept_default_model", "culture_default_model"),
            },
        ),
        (
            _("Evaluation Gates"),
            {
                "classes": ["tab"],
                "fields": (
                    "format_gate_default_model",
                    "culture_gate_default_model",
                    "concept_gate_default_model",
                    "brand_gate_default_model",
                ),
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
    readonly_fields = ["created_at", "updated_at"]

    def has_add_permission(self, request):
        return not PipelineSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
