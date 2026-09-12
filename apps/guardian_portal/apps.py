"""Configuração da app `guardian_portal`."""

from django.apps import AppConfig


class GuardianPortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.guardian_portal"
    label = "guardian_portal"
    verbose_name = "Portal do Encarregado de Educação"
