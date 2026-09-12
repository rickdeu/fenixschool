"""Tests for tenant isolation via `TenantQuerySet`/`TenantManager` (issue #4)."""

import uuid

import pytest

from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db


def test_objects_returns_nothing_without_an_active_tenant_context(
    synced_model_class, institution_factory
):
    institution = institution_factory()
    synced_model_class.objects.create(institution=institution, origin_node_id=uuid.uuid4())

    assert synced_model_class.objects.count() == 0


def test_institution_a_never_sees_institution_bs_records_via_objects(
    synced_model_class, institution_factory
):
    institution_a = institution_factory("Institution A")
    institution_b = institution_factory("Institution B")

    record_a = synced_model_class.objects.create(
        institution=institution_a, origin_node_id=uuid.uuid4()
    )
    synced_model_class.objects.create(institution=institution_b, origin_node_id=uuid.uuid4())

    with tenant_context(institution_a.id):
        results = list(synced_model_class.objects.all())

    assert results == [record_a]


def test_all_objects_ignores_the_tenant_context(synced_model_class, institution_factory):
    institution_a = institution_factory("Institution A")
    institution_b = institution_factory("Institution B")
    synced_model_class.objects.create(institution=institution_a, origin_node_id=uuid.uuid4())
    synced_model_class.objects.create(institution=institution_b, origin_node_id=uuid.uuid4())

    with tenant_context(institution_a.id):
        assert synced_model_class.all_objects.count() == 2

    assert synced_model_class.all_objects.count() == 2


def test_objects_hides_soft_deleted_records(synced_model_class, institution_factory):
    institution = institution_factory()
    synced_model_class.objects.create(
        institution=institution, origin_node_id=uuid.uuid4(), is_deleted=True
    )

    with tenant_context(institution.id):
        assert synced_model_class.objects.count() == 0
        assert synced_model_class.all_objects.count() == 1


def test_tenant_context_does_not_leak_across_blocks(synced_model_class, institution_factory):
    institution_a = institution_factory("Institution A")
    institution_b = institution_factory("Institution B")
    synced_model_class.objects.create(institution=institution_a, origin_node_id=uuid.uuid4())
    synced_model_class.objects.create(institution=institution_b, origin_node_id=uuid.uuid4())

    with tenant_context(institution_a.id):
        assert synced_model_class.objects.count() == 1

    assert synced_model_class.objects.count() == 0

    with tenant_context(institution_b.id):
        assert synced_model_class.objects.count() == 1
