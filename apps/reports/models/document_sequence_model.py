"""Contador sequencial de numeração de documentos oficiais (RF-REL-06,
issue #93): um por instituição/tipo de documento, nunca reiniciado.

Não é exposto em nenhum ecrã -- é usado exclusivamente por
`apps.reports.services._reserve_document_number`, sob `select_for_update()`,
para garantir que dois pedidos de emissão em simultâneo nunca recebem o
mesmo número.
"""

from django.db import models

from apps.core.models import SyncedModel


class DocumentSequence(SyncedModel):
    """ "Sequência de Documento" -- último número emitido de um tipo de
    documento (ex. "declaracao-matricula", "pauta-oficial") nesta
    instituição."""

    document_type = models.CharField("tipo de documento", max_length=50)
    last_number = models.PositiveIntegerField("último número emitido", default=0)

    class Meta:
        verbose_name = "sequência de documento"
        verbose_name_plural = "sequências de documento"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "document_type"],
                name="unique_document_sequence_per_institution_and_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} — {self.institution} ({self.last_number})"
