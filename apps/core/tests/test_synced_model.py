"""Tests for the `SyncedModel` mixin (issue #3) — see docs/04-arquitetura-tecnica.md §4.5."""

import time
import uuid

import pytest

pytestmark = pytest.mark.django_db


def test_id_is_a_uuid7_generated_automatically(synced_model_class, institution_factory):
    institution = institution_factory()
    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4()
    )

    assert isinstance(instance.id, uuid.UUID)
    assert instance.id.version == 7


def test_uuid7_ids_are_sortable_by_creation_time(synced_model_class, institution_factory):
    institution = institution_factory()
    first = synced_model_class.objects.create(institution=institution, origin_node_id=uuid.uuid4())
    time.sleep(0.001)
    second = synced_model_class.objects.create(institution=institution, origin_node_id=uuid.uuid4())

    assert str(first.id) < str(second.id)


def test_cross_cutting_fields_have_the_expected_defaults(synced_model_class, institution_factory):
    institution = institution_factory()
    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4()
    )

    assert instance.version == 1
    assert instance.is_deleted is False
    assert instance.created_at is not None
    assert instance.updated_at is not None
    assert instance.updated_by is None


def test_updated_at_changes_on_save(synced_model_class, institution_factory):
    institution = institution_factory()
    instance = synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4()
    )
    original_updated_at = instance.updated_at

    time.sleep(0.001)
    instance.name = "changed"
    instance.save()
    instance.refresh_from_db()

    assert instance.updated_at > original_updated_at


def test_institution_and_is_deleted_are_indexed(synced_model_class):
    institution_field = synced_model_class._meta.get_field("institution")
    is_deleted_field = synced_model_class._meta.get_field("is_deleted")

    # Django indexes a ForeignKey column by default unless `db_index=False` is set.
    assert institution_field.db_index is not False
    assert is_deleted_field.db_index is True

    indexed_field_sets = {tuple(sorted(index.fields)) for index in synced_model_class._meta.indexes}
    assert ("institution", "is_deleted") in indexed_field_sets


def test_institution_is_required(synced_model_class):
    institution_field = synced_model_class._meta.get_field("institution")

    assert institution_field.null is False
    assert institution_field.blank is False
