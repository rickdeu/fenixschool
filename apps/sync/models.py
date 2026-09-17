"""Data model backing the sync engine — see docs/05-modelo-de-dados.md §5.26 and
docs/08-offline-first-e-sincronizacao.md §8.3-§8.5.

- `Node`: the identity of each Local/Central node (issue #123).
- `ChangeRecord` ("RegistoAlteracao"): the outbox/changelog table -- one row per
  business change to sync (issue #120). Written by the generic signal in
  `apps/sync/signals.py` (issue #124), never by application code directly.
- `SyncSession` ("SessaoSincronizacao"): one row per sync attempt, for
  resumability and the sync status panel (RF-ADM-04, issue #121).

`Conflito` (the conflict queue, §8.6) is not part of this M0 foundation batch --
it belongs with the push/pull endpoints that actually detect conflicts (M5).
"""

from django.db import models
from uuid6 import uuid7


class Node(models.Model):
    """A Local or Central node's identity, used to authenticate its sync requests.

    Does not inherit `SyncedModel`: it *is* part of the sync infrastructure
    itself (much like `core.Institution` is the tenant, not a tenant-owned
    record).
    """

    class NodeType(models.TextChoices):
        LOCAL = "local", "Nó Local"
        CENTRAL = "central", "Nó Central"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    node_type = models.CharField("tipo", max_length=10, choices=NodeType.choices)
    institution = models.ForeignKey(
        "core.Institution",
        verbose_name="instituição",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nodes",
        help_text="Obrigatório para um Nó Local; um Nó Central agrega várias instituições.",
    )
    public_key = models.TextField(
        "chave pública",
        help_text=(
            "Gerada no setup wizard da instalação e nunca reutilizada entre nós -- "
            "usada na autenticação mútua da sincronização (§8.5)."
        ),
    )
    last_synced_at = models.DateTimeField("última sincronização", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "node"
        verbose_name_plural = "nodes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(node_type="local", institution__isnull=False)
                    | models.Q(node_type="central", institution__isnull=True)
                ),
                name="sync_node_institution_matches_type",
                violation_error_message=(
                    "Um Nó Local requer uma instituição; um Nó Central não tem uma fixa."
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_node_type_display()} ({self.institution or 'multi-instituição'})"


class ChangeRecord(models.Model):
    """The outbox/changelog table ("RegistoAlteracao", §5.26) -- one row per
    `create`/`update`/`delete` on a `SyncedModel` instance, written in the same
    transaction as the business change (§8.4) by the generic signal in
    `apps/sync/signals.py`.
    """

    class Operation(models.TextChoices):
        CREATE = "create", "Criação"
        UPDATE = "update", "Actualização"
        DELETE = "delete", "Eliminação"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    entity = models.CharField(
        "entidade",
        max_length=255,
        help_text='"app_label.model_name" da entidade alterada (ex. "grading.nota").',
    )
    entity_id = models.UUIDField("id da entidade")
    operation = models.CharField("operação", max_length=10, choices=Operation.choices)
    payload = models.JSONField(
        "payload", help_text="Estado da entidade após a alteração, serializado."
    )
    origin_node_id = models.UUIDField(
        "node de origem", help_text="O node onde esta alteração foi originalmente criada."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(
        "sincronizado em",
        null=True,
        blank=True,
        help_text="NULL enquanto pendente de envio/aplicação.",
    )

    class Meta:
        verbose_name = "registo de alteração"
        verbose_name_plural = "registos de alteração"
        ordering = ["created_at"]
        indexes = [
            # Supports the pending-records query the sync worker/panel run
            # constantly ("WHERE synced_at IS NULL") -- see RF-ADM-04.
            models.Index(fields=["synced_at"], name="sync_changerecord_pending_idx"),
            models.Index(fields=["entity", "entity_id"], name="sync_changerecord_entity_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_operation_display()} {self.entity}#{self.entity_id}"


class SyncSession(models.Model):
    """One row per sync attempt ("SessaoSincronizacao", §5.26) -- lets the sync
    worker resume a partial attempt and the sync status panel (RF-ADM-04) show
    history.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Em curso"
        SUCCEEDED = "succeeded", "Concluída"
        FAILED = "failed", "Falhou"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    node = models.ForeignKey(
        Node, verbose_name="node", on_delete=models.CASCADE, related_name="sync_sessions"
    )
    started_at = models.DateTimeField("iniciada em", auto_now_add=True)
    finished_at = models.DateTimeField("concluída em", null=True, blank=True)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    records_sent = models.PositiveIntegerField("registos enviados", default=0)
    records_received = models.PositiveIntegerField("registos recebidos", default=0)
    errors = models.JSONField("erros", default=list, blank=True)

    class Meta:
        verbose_name = "sessão de sincronização"
        verbose_name_plural = "sessões de sincronização"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.node} — {self.get_status_display()} ({self.started_at:%Y-%m-%d %H:%M})"
