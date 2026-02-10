"""URL configuration for audiences app."""

from django.urls import path

from . import views

app_name = "audiences"

urlpatterns = [
    path(
        "ajax/segment-vectors/",
        views.get_segment_vectors,
        name="segment_vectors",
    ),
    path(
        "ajax/segment-values/",
        views.get_segment_values,
        name="segment_values",
    ),
    path(
        "ajax/add-segment/",
        views.add_segment_to_persona,
        name="add_segment",
    ),
    path(
        "ajax/remove-segment/",
        views.remove_segment_from_persona,
        name="remove_segment",
    ),
]
