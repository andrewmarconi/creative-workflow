"""Forms for audience admin interface."""

from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Persona, PersonaSegment, Segment


class SegmentBuilderWidget(forms.Widget):
    """Custom widget for building persona segments with cascading dropdowns.

    Provides a three-step interface:
    1. Select category (DEMOGRAPHIC, BEHAVIORAL, PSYCHOGRAPHIC)
    2. Select vector (filtered by category)
    3. Select value (filtered by vector)
    4. Add segment button
    """

    template_name = "audiences/admin/segment_builder.html"

    def get_context(self, name, value, attrs):
        """Prepare context for template rendering."""
        context = super().get_context(name, value, attrs)

        # Get all categories
        categories = Segment.CATEGORY_CHOICES

        # Get existing segments for this persona
        existing_segments = []
        if value:  # value is persona_id
            existing_segments = list(
                PersonaSegment.objects.filter(persona_id=value)
                .select_related("segment")
                .order_by("segment__category", "segment__vector", "segment__value")
            )

        context.update({
            "categories": categories,
            "existing_segments": existing_segments,
            "persona_id": value,
            "ajax_vectors_url": reverse("audiences:segment_vectors"),
            "ajax_values_url": reverse("audiences:segment_values"),
        })

        return context

    def value_from_datadict(self, data, files, name):
        """Extract value from POST data (not used for this widget)."""
        return data.get(name)


class PersonaAdminForm(forms.ModelForm):
    """Custom form for Persona admin."""

    class Meta:
        model = Persona
        fields = "__all__"
