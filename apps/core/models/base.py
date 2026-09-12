"""The `SyncedModel` abstract mixin — cross-cutting fields shared by every business entity.

See docs/04-arquitetura-tecnica.md §4.4 (multi-tenancy) / §4.5 (identifiers and the
distributed data model) and docs/05-modelo-de-dados.md ("Convenções transversais").
Every business model (academic, enrollment, grading, finance, etc.) should inherit
`SyncedModel` instead of `models.Model` directly.
"""

from django.conf import settings
from django.db import models
from uuid6 import uuid7


class SyncedModel(models.Model):
    """Fields and behaviour shared by every syncable business entity.

    - ``id``: UUID v7 (time-sortable), generated at the node of origin — lets the
      central node merge data coming from multiple local nodes without primary
      key collisions (§4.5).
    - ``institution``: the tenant that owns the record (multi-tenant isolation,
      §4.4). Never `null` — every business entity belongs to exactly one
      institution.
    - ``origin_node_id``: identifies the node (local or central) where the record
      was created — needed by the sync engine to tell where each change came
      from.
    - ``updated_by``: points at ``settings.AUTH_USER_MODEL`` rather than a
      hardcoded user model, which is Django's own recommended way of referencing
      "the" user model from reusable code.
    - ``version``: optimistic concurrency-control counter.
    - ``is_deleted``: soft-delete — academic/financial data is never physically
      removed.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    institution = models.ForeignKey(
        "core.Institution",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )
    origin_node_id = models.UUIDField(
        help_text="The node (local or central) where this record was originally created.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated_set",
    )
    version = models.PositiveIntegerField(default=1)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=["institution", "is_deleted"],
                name="%(app_label)s_%(class)s_tenant_idx",
            ),
        ]
