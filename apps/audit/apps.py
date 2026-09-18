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
        from apps.grading.models import FinalGrade, Grade

        from .signals import audit_group_membership, audit_model

        # RNF-AUD-01's 5 critical entities: Utilizador/Matrícula/Nota exist
        # today -- Pagamento is wired the same way once finance builds it
        # (see this module's own docstring for the reasoning). `FinalGrade`
        # ("Média") isn't one of the original 5, but issue #58's own "ajuste
        # manual exige justificação registada em auditoria" acceptance
        # criterion needs exactly this: every create/update, including a
        # manual override's `manual_override_value`/`override_reason`/
        # `overridden_by`, ends up in the same audit trail, for free, via
        # this generic before/after diff.
        audit_model(User, exclude=frozenset({"password"}))
        audit_model(Enrollment)
        audit_model(Grade)
        audit_model(FinalGrade)
        audit_group_membership(User.groups.through)
