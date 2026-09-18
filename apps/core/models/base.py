"""The `SyncedModel` abstract mixin — cross-cutting fields shared by every business entity.

See docs/04-arquitetura-tecnica.md §4.4 (multi-tenancy) / §4.5 (identifiers and the
distributed data model) and docs/05-modelo-de-dados.md ("Convenções transversais").
Every business model (academic, enrollment, grading, finance, etc.) should inherit
`SyncedModel` instead of `models.Model` directly.
"""

from django.conf import settings
from django.db import models
from uuid6 import uuid7

from .managers import TenantManager, TenantQuerySet


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

    ``objects`` (via `TenantManager`, see `apps.core.models.managers`) always
    filters by the institution of the current tenant context and hides
    soft-deleted records. ``all_objects`` shares the same `TenantQuerySet` (so
    `for_institution`/`for_request` are available on it too, for code that
    wants to filter explicitly without depending on the ambient tenant
    context) but does not override `get_queryset()`, so plain `all_objects.all()`
    is genuinely unfiltered — **restricted use**: system tasks (the sync
    engine, the Super Administrator area), never code that serves an ordinary
    user's request.
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

    objects = TenantManager()
    # Deliberately not a second named manager class: this is exactly
    # `TenantManager`'s own queryset, just without the tenant-filtering
    # `get_queryset()` override, so it is spelled out via the same
    # `from_queryset()` factory `TenantManager` itself is built from instead
    # of via a subclass that would exist only to restate that in prose.
    all_objects = models.Manager.from_queryset(TenantQuerySet)()  # noqa: DJ012 -- ruff only recognizes "objects"

    class Meta:
        abstract = True
        # Django uses the model's *base* manager (the first one defined, by
        # default) for internal operations that must see every row regardless of
        # filtering -- e.g. collecting related objects for an on_delete=PROTECT
        # check. Since `objects` here can legitimately return an empty queryset
        # when no tenant context is active, that default would be unsafe: it
        # could make Django think a to-be-deleted row has no related records
        # when it simply couldn't see them. Pointing `base_manager_name` at the
        # unfiltered `all_objects` keeps those internal checks correct.
        base_manager_name = "all_objects"
        indexes = [
            # No explicit `name=`: Django auto-generates one (a truncated,
            # hash-suffixed name guaranteed to fit its own 30-character
            # index-name limit) instead. A manual "%(app_label)s_%(class)s_..."
            # template can't make that guarantee -- it already overflowed for
            # `academic.CurricularYear`/`SchoolClass` (issues #33/#34).
            models.Index(fields=["institution", "is_deleted"]),
        ]
