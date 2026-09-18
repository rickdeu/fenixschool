"""Configuração da app `audit`."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Auditoria"

    def ready(self) -> None:
        from apps.accounts.models import User
        from apps.enrollment.models import Enrollment

        from .signals import audit_group_membership, audit_model

        # RNF-AUD-01's 5 critical entities: only Utilizador/Matrícula exist
        # today -- Nota/Pagamento are wired the same way once grading/finance
        # build them (see this module's own docstring for the reasoning).
        audit_model(User, exclude=frozenset({"password"}))
        audit_model(Enrollment)
        audit_group_membership(User.groups.through)
