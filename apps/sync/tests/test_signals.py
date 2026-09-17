"""Tests for the generic outbox signal (issue #124, docs/08-offline-first-e-
sincronizacao.md §8.4): every change to a `SyncedModel` instance writes exactly
one `ChangeRecord`, atomically with the business change."""

import uuid

import pytest
from django.db import transaction

from apps.sync.models import ChangeRecord

pytestmark = pytest.mark.django_db


def test_creating_a_synced_model_writes_exactly_one_create_change_record(
    synced_model_class, institution_factory
):
    institution = institution_factory()
    origin_node_id = uuid.uuid4()

    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=origin_node_id, name="Alice"
    )

    records = ChangeRecord.objects.filter(entity_id=instance.pk)
    assert records.count() == 1
    record = records.get()
    assert record.entity == f"{instance._meta.app_label}.{instance._meta.model_name}"
    assert record.operation == ChangeRecord.Operation.CREATE
    assert record.origin_node_id == origin_node_id
    assert record.synced_at is None
    assert record.payload["fields"]["name"] == "Alice"


def test_updating_a_synced_model_writes_an_update_change_record_and_bumps_version(
    synced_model_class, institution_factory
):
    institution = institution_factory()
    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4(), name="Alice"
    )
    assert instance.version == 1

    instance.name = "Alice Updated"
    instance.save()

    assert instance.version == 2
    update_records = ChangeRecord.objects.filter(
        entity_id=instance.pk, operation=ChangeRecord.Operation.UPDATE
    )
    assert update_records.count() == 1
    assert update_records.get().payload["fields"]["version"] == 2


def test_deleting_a_synced_model_writes_a_delete_change_record(
    synced_model_class, institution_factory
):
    institution = institution_factory()
    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4(), name="Alice"
    )
    instance_id = instance.pk

    instance.delete()

    delete_records = ChangeRecord.objects.filter(
        entity_id=instance_id, operation=ChangeRecord.Operation.DELETE
    )
    assert delete_records.count() == 1


def test_change_record_is_not_written_for_a_plain_non_synced_model(institution_factory):
    # `Institution` itself is a plain `models.Model`, not a `SyncedModel` --
    # creating one must not produce a `ChangeRecord`.
    institution = institution_factory()

    assert not ChangeRecord.objects.filter(entity_id=institution.pk).exists()


def test_change_record_rolls_back_with_its_business_transaction(
    synced_model_class, institution_factory
):
    institution = institution_factory()

    class DeliberateFailure(Exception):
        pass

    instance_id = None
    with pytest.raises(DeliberateFailure):
        with transaction.atomic():
            instance = synced_model_class.objects.create(
                institution=institution, origin_node_id=uuid.uuid4(), name="Rolled back"
            )
            instance_id = instance.pk
            # Sanity check: the ChangeRecord exists *inside* the still-open
            # transaction, before it gets rolled back below.
            assert ChangeRecord.objects.filter(entity_id=instance_id).exists()
            raise DeliberateFailure()

    assert not synced_model_class.objects.filter(pk=instance_id).exists()
    assert not ChangeRecord.objects.filter(entity_id=instance_id).exists()
