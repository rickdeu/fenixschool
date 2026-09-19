"""Configuração da app `enrollment`."""

from django.apps import AppConfig


class EnrollmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.enrollment"
    label = "enrollment"
    verbose_name = "Matrículas"

    def ready(self) -> None:
        from . import signals  # noqa: F401 -- connects its @receiver-decorated functions
