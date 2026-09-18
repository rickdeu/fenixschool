"""Modelo Registo de Auditoria (RNF-AUD-01/03, docs/05-modelo-de-dados.md
§5.27, docs/09-seguranca-e-privacidade.md §9.4, issue #140).

Not a `SyncedModel`: §5.27 doesn't list an `institution` field, and an audit
trail legitimately needs to outlive/precede tenant-scoped filtering (e.g. an
Administrador da Instituição action is still auditable even if something
about the tenant context around it is unusual) -- see
`apps.audit.signals.audit_model` for how entries actually get created.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from uuid6 import uuid7


class AuditLogEntry(models.Model):
    """ "Registo de Auditoria" -- one row per create/update/delete of a
    critical entity (RNF-AUD-01: Nota, Matrícula, Pagamento, Utilizador,
    Permissão)."""

    class Action(models.TextChoices):
        CREATE = "create", "Criação"
        UPDATE = "update", "Alteração"
        DELETE = "delete", "Eliminação"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilizador",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_log_entries",
        help_text="Quem realizou a acção -- vazio para acções de sistema sem utilizador.",
    )
    action = models.CharField("acção", max_length=10, choices=Action.choices)
    entity = models.CharField(
        "entidade", max_length=100, help_text='"app_label.ModelName", ex. "enrollment.Enrollment".'
    )
    entity_id = models.CharField("id da entidade", max_length=64)
    values_before = models.JSONField(
        "valores antes", default=dict, blank=True, encoder=DjangoJSONEncoder
    )
    values_after = models.JSONField(
        "valores depois", default=dict, blank=True, encoder=DjangoJSONEncoder
    )
    ip_address = models.GenericIPAddressField("IP de origem", null=True, blank=True)
    timestamp = models.DateTimeField("data/hora", auto_now_add=True)

    class Meta:
        verbose_name = "registo de auditoria"
        verbose_name_plural = "registos de auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity", "entity_id"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} — {self.entity}#{self.entity_id} ({self.timestamp})"

    def save(self, *args, **kwargs):
        # RNF-AUD-01/§9.4: "Registos de auditoria são imutáveis (sem
        # update/delete disponível via aplicação; apenas rotina de
        # retenção administrada directamente na base de dados)".
        # `self.pk` is not a reliable "already exists" check here: it's a
        # UUID generated client-side (`default=uuid7`), already set before
        # the very first save -- `_state.adding` is Django's own correct
        # signal for "this instance has never been saved yet".
        if not self._state.adding:
            raise ValidationError("Um registo de auditoria não pode ser alterado depois de criado.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Um registo de auditoria não pode ser eliminado através da aplicação."
        )
