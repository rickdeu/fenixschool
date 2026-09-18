"""Signals genéricos de auditoria (issue #140, RNF-AUD-01).

`audit_model(Model, exclude=...)` wires up automatic `AuditLogEntry`
creation for every create/update/(soft or hard) delete of `Model` -- call it
once per critical entity from `AuditConfig.ready()` (see `apps/audit/apps.py`).
Of RNF-AUD-01's 5 critical entities (Nota, Matrícula, Pagamento, Utilizador,
Permissão), only `enrollment.Enrollment` (Matrícula) and `accounts.User`
(Utilizador) exist today -- `grading.Nota`/`finance.Pagamento` don't exist
yet (see docs/implementation-decisions.md). Wire them the same way once
they do.
"""

from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

from .context import get_current_ip_address, get_current_user
from .models import AuditLogEntry


def _snapshot(instance, exclude):
    """A JSON-safe dict of every concrete (non-M2M) field on `instance` --
    `field.value_from_object()` returns a FK's raw id rather than the
    related object, and `AuditLogEntry.values_before/after`'s
    `DjangoJSONEncoder` handles dates/UUIDs/Decimals from there."""
    return {
        field.name: field.value_from_object(instance)
        for field in instance._meta.concrete_fields
        if field.name not in exclude
    }


def _record(sender, instance, action, before, after):
    AuditLogEntry.objects.create(
        user=get_current_user(),
        action=action,
        entity=sender._meta.label,
        entity_id=str(instance.pk),
        values_before=before,
        values_after=after,
        ip_address=get_current_ip_address(),
    )


def audit_model(model, *, exclude: frozenset = frozenset()) -> None:
    """Connects the 3 signals below for `model`. `exclude` names fields to
    leave out of every snapshot -- e.g. `password` for `accounts.User`,
    never worth (or safe) to keep in a readable audit trail."""

    def pre_save_handler(sender, instance, **kwargs):
        # `_base_manager` (not `objects`): for a `SyncedModel`, that's
        # `all_objects` (see `apps.core.models.base.SyncedModel.Meta`) --
        # bypasses tenant-context/soft-delete filtering, since an audit
        # snapshot must reflect the row's true prior DB state regardless of
        # the ambient tenant context the write happens to run under.
        try:
            existing = sender._base_manager.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._audit_before = {}
        else:
            instance._audit_before = _snapshot(existing, exclude)

    def post_save_handler(sender, instance, created, **kwargs):
        before = getattr(instance, "_audit_before", {})
        after = _snapshot(instance, exclude)

        if created:
            action = AuditLogEntry.Action.CREATE
        elif before.get("is_deleted") is False and after.get("is_deleted") is True:
            # A `SyncedModel`'s soft-delete is, at the database level, just
            # another UPDATE -- but it's a deletion from RNF-AUD-01's point
            # of view, so it's logged as one.
            action = AuditLogEntry.Action.DELETE
        elif before == after:
            return
        else:
            action = AuditLogEntry.Action.UPDATE

        _record(sender, instance, action, before, after)

    def post_delete_handler(sender, instance, **kwargs):
        _record(sender, instance, AuditLogEntry.Action.DELETE, _snapshot(instance, exclude), {})

    # `weak=False`: these are closures, which Django's default weak-reference
    # dispatch would otherwise garbage-collect almost immediately.
    pre_save.connect(pre_save_handler, sender=model, weak=False)
    post_save.connect(post_save_handler, sender=model, weak=False)
    post_delete.connect(post_delete_handler, sender=model, weak=False)


def audit_group_membership(model) -> None:
    """RNF-AUD-01's "Permissão" critical entity: a `User`'s own group
    membership changing is the one real, already-existing form of
    permission change in the system today (RBAC is Django Groups-based --
    see `accounts.migrations.0003_profile_groups`) -- logged as an
    `accounts.User` UPDATE, since it's the user's own access that changed.
    """

    def handler(sender, instance, action, pk_set, **kwargs):
        if action not in {"post_add", "post_remove", "post_clear"}:
            return
        _record(
            type(instance),
            instance,
            AuditLogEntry.Action.UPDATE,
            {},
            {"groups_changed": action, "group_ids": sorted(str(pk) for pk in (pk_set or ()))},
        )

    m2m_changed.connect(handler, sender=model, weak=False)
