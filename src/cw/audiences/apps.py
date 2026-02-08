"""Audiences app configuration."""

from django.apps import AppConfig


class AudiencesConfig(AppConfig):
    """Configuration for the audiences app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cw.audiences"
    verbose_name = "Audiences"
