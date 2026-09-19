"""Configuração da app `reports`."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    label = "reports"
    verbose_name = "Relatórios"

    def ready(self) -> None:
        from apps.audit.signals import audit_model

        from .models import IssuedDocument

        # RF-REL-06 (issue #93): "toda emissão regista entrada de
        # auditoria" -- de graça, via o mesmo mecanismo genérico já usado
        # por Grade/Enrollment/User (`apps.audit.apps.AuditConfig.ready`).
        audit_model(IssuedDocument)
