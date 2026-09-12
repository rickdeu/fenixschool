"""Configuração da app `grading`."""

from django.apps import AppConfig


class GradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.grading"
    label = "grading"
    verbose_name = "Avaliação e Notas"
