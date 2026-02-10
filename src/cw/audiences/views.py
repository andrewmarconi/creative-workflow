"""AJAX views for audience admin interface."""

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Persona, PersonaSegment, Segment


@staff_member_required
def get_segment_vectors(request):
    """Get unique vectors for a given segment category.

    Used for cascading dropdown in persona segment builder.
    """
    category = request.GET.get("category")
    if not category:
        return JsonResponse({"vectors": []})

    vectors = (
        Segment.objects.filter(category=category, is_active=True)
        .values_list("vector", flat=True)
        .distinct()
        .order_by("vector")
    )

    return JsonResponse({"vectors": list(vectors)})


@staff_member_required
def get_segment_values(request):
    """Get segment values for a given category and vector.

    Used for cascading dropdown in persona segment builder.
    Returns full segment data (id, value, description).
    """
    category = request.GET.get("category")
    vector = request.GET.get("vector")

    if not category or not vector:
        return JsonResponse({"segments": []})

    segments = Segment.objects.filter(
        category=category,
        vector=vector,
        is_active=True
    ).values("id", "value", "description").order_by("value")

    return JsonResponse({"segments": list(segments)})


@staff_member_required
@require_POST
def add_segment_to_persona(request):
    """Add a segment to a persona.

    Used by the segment builder to attach segments.
    """
    try:
        data = json.loads(request.body)
        persona_id = data.get("persona_id")
        segment_id = data.get("segment_id")

        if not persona_id or not segment_id:
            return JsonResponse({"success": False, "error": "Missing parameters"})

        persona = Persona.objects.get(pk=persona_id)
        segment = Segment.objects.get(pk=segment_id)

        # Create the relationship if it doesn't exist
        PersonaSegment.objects.get_or_create(
            persona=persona,
            segment=segment
        )

        return JsonResponse({"success": True})

    except (Persona.DoesNotExist, Segment.DoesNotExist):
        return JsonResponse({"success": False, "error": "Persona or Segment not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
@require_POST
def remove_segment_from_persona(request):
    """Remove a segment from a persona.

    Used by the segment builder to detach segments.
    """
    try:
        data = json.loads(request.body)
        persona_id = data.get("persona_id")
        segment_id = data.get("segment_id")

        if not persona_id or not segment_id:
            return JsonResponse({"success": False, "error": "Missing parameters"})

        PersonaSegment.objects.filter(
            persona_id=persona_id,
            segment_id=segment_id
        ).delete()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
