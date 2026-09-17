"""The outbox pattern's generic capture (issue #124, docs/08-offline-first-e-
sincronizacao.md §8.4): every `create`/`update`/`delete` on *any* `SyncedModel`
subclass, in *any* app, writes exactly one `ChangeRecord` -- in the same
transaction as the business change, since Django signals fire synchronously
inside whatever transaction the caller's `.save()`/`.delete()` already opened.

Connected once here, for every model in the project, rather than once per
business app -- see `SyncConfig.ready()`.
"""

import json

from django.core import serializers
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.models import SyncedModel

from .models import ChangeRecord


@receiver(pre_save)
def bump_version_before_update(sender, instance, raw, **kwargs):
    """Increment `SyncedModel.version` right before an update is written.

    Not on create (`version` already starts at 1, its model default) and not
    during fixture loading (`raw=True`), which must preserve the version the
    fixture itself specifies.
    """
    if raw or not isinstance(instance, SyncedModel):
        return
    if not instance._state.adding:
        instance.version = (instance.version or 0) + 1


@receiver(post_save)
def record_change_on_save(sender, instance, created, raw, **kwargs):
    if raw or not isinstance(instance, SyncedModel):
        return
    _write_change_record(
        instance,
        operation=ChangeRecord.Operation.CREATE if created else ChangeRecord.Operation.UPDATE,
    )


@receiver(post_delete)
def record_change_on_delete(sender, instance, **kwargs):
    if not isinstance(instance, SyncedModel):
        return
    _write_change_record(instance, operation=ChangeRecord.Operation.DELETE)


def _write_change_record(instance, *, operation):
    # `serializers.serialize` (rather than e.g. `model_to_dict`) is what makes
    # this genuinely generic: it introspects *every* concrete field from
    # `instance._meta`, including non-editable ones like `SyncedModel.id`,
    # with no per-model configuration.
    payload = json.loads(serializers.serialize("json", [instance]))[0]
    ChangeRecord.objects.create(
        entity=f"{instance._meta.app_label}.{instance._meta.model_name}",
        entity_id=instance.pk,
        operation=operation,
        payload=payload,
        origin_node_id=instance.origin_node_id,
    )
