"""Registo de emissão de documento oficial (RF-REL-06, issue #93):
"numeração/série única" + auditoria da emissão -- a base reutilizável para
todo documento oficial (declarações, pautas, boletins, ...) que as issues
#94/#96/#97 vêm construir em cima desta.

Não é `SyncedModel`-editável depois de criado: como `audit.AuditLogEntry`,
é um registo histórico imutável (o próprio número/série só tem valor
probatório se nunca puder ser alterado depois de emitido) -- ver `save()`/
`delete()`.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel


class IssuedDocument(SyncedModel):
    """ "Documento Emitido" -- um registo por cada documento oficial gerado,
    com o número/série (`formatted_number`) reservado por
    `apps.reports.services._reserve_document_number`."""

    document_type = models.CharField(
        "tipo de documento",
        max_length=50,
        help_text='Identificador curto do tipo de documento, ex. "declaracao-matricula".',
    )
    number = models.PositiveIntegerField("número")
    formatted_number = models.CharField(
        "número/série",
        max_length=80,
        help_text='Ex. "DECLARACAO-MATRICULA/2026/000123".',
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="emitido por",
        on_delete=models.PROTECT,
        related_name="issued_documents",
    )

    class Meta:
        verbose_name = "documento emitido"
        verbose_name_plural = "documentos emitidos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "formatted_number"],
                name="unique_issued_document_formatted_number_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.formatted_number

    def save(self, *args, **kwargs):
        # Mesma lógica de imutabilidade de `audit.AuditLogEntry.save()`:
        # `_state.adding` (não `self.pk`) é o sinal correcto de "nunca
        # gravado antes", já que o `pk` é um UUID gerado no cliente.
        if not self._state.adding:
            raise ValidationError("Um documento emitido não pode ser alterado depois de criado.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Um documento emitido não pode ser eliminado através da aplicação.")
