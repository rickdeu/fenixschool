"""`TenantQuerySet`/`TenantManager` — automatic isolation by institution (tenant).

See docs/04-arquitetura-tecnica.md §4.4 (column-based multi-tenancy, applied
uniformly across the whole stack) and `apps.core.context` for the "current
context" mechanism this manager reads.
"""

from django.db import models

from apps.core.context import get_current_institution


class TenantQuerySet(models.QuerySet):
    """A tenant-aware QuerySet, used by `TenantManager` and by `all_objects`."""

    def for_institution(self, institution_id):
        """Filter explicitly by an institution, hiding soft-deleted records."""
        return self.filter(institution_id=institution_id, is_deleted=False)

    def for_request(self, request):
        """Shortcut to filter by the institution already resolved for the current HTTP request.

        Expects `request.institution_id` to already be set — typically by
        `core.middleware.TenantMiddleware` (#5). Returns an empty queryset if the
        request does not have that value yet.
        """
        return self.for_institution(getattr(request, "institution_id", None))


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """The tenant-aware manager used as `objects` on every `SyncedModel`.

    Always filters by the institution of the current context
    (`apps.core.context.get_current_institution`) and hides soft-deleted
    records. When no tenant context is active at all (e.g. a script or task
    that forgot to set one), it returns an **empty** queryset — failing closed
    instead of accidentally exposing every institution's data by default.

    **`Model.all_objects` is for restricted, system-level use only** (no
    filtering at all, soft-deleted records included): the sync engine, the
    Super Administrator area, maintenance commands. It should never appear in
    code that directly serves an ordinary user's request; flag it in code
    review whenever it turns up outside those contexts (see also
    docs/13-testes-e-qualidade.md).
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        institution_id = get_current_institution()
        if institution_id is None:
            return queryset.none()
        return queryset.for_institution(institution_id)


class UnfilteredTenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """The unfiltered manager used as `all_objects` on every `SyncedModel`.

    Unlike `TenantManager`, `get_queryset()` here is the plain, unfiltered
    default -- `all_objects.all()` really does return every institution's
    records, soft-deleted included. It still shares `TenantQuerySet`, though,
    so restricted system code that has a `request` (or an institution id) at
    hand can filter explicitly and intentionally, e.g.
    `Model.all_objects.for_request(request)`, without depending on -- or being
    silently bound to -- whatever the ambient tenant context happens to be.
    """
