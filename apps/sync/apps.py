"""Configuração da app `sync`."""

from django.apps import AppConfig


class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sync"
    label = "sync"
    verbose_name = "Sincronização"

    def ready(self) -> None:
        from . import signals  # noqa: F401 -- connects its @receiver-decorated functions
