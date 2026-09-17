"""Tests for `Node`, `ChangeRecord` and `SyncSession` (issues #120, #121, #123)."""

import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.sync.models import ChangeRecord, Node, SyncSession

pytestmark = pytest.mark.django_db


def test_local_node_requires_an_institution(institution_factory):
    institution = institution_factory()

    node = Node.objects.create(
        node_type=Node.NodeType.LOCAL, institution=institution, public_key="key"
    )

    assert node.institution == institution


def test_local_node_without_an_institution_is_rejected():
    with transaction.atomic(), pytest.raises(IntegrityError):
        Node.objects.create(node_type=Node.NodeType.LOCAL, institution=None, public_key="key")


def test_central_node_cannot_have_a_fixed_institution(institution_factory):
    institution = institution_factory()

    with transaction.atomic(), pytest.raises(IntegrityError):
        Node.objects.create(
            node_type=Node.NodeType.CENTRAL, institution=institution, public_key="key"
        )


def test_central_node_has_no_institution():
    node = Node.objects.create(node_type=Node.NodeType.CENTRAL, institution=None, public_key="key")

    assert node.institution is None


def test_change_record_pending_query_uses_synced_at_is_null():
    pending = ChangeRecord.objects.create(
        entity="grading.nota",
        entity_id=uuid.uuid4(),
        operation=ChangeRecord.Operation.CREATE,
        payload={"foo": "bar"},
        origin_node_id=uuid.uuid4(),
    )
    already_synced = ChangeRecord.objects.create(
        entity="grading.nota",
        entity_id=uuid.uuid4(),
        operation=ChangeRecord.Operation.CREATE,
        payload={"foo": "bar"},
        origin_node_id=uuid.uuid4(),
        synced_at="2026-01-01T00:00:00Z",
    )

    pending_ids = set(
        ChangeRecord.objects.filter(synced_at__isnull=True).values_list("id", flat=True)
    )

    assert pending.id in pending_ids
    assert already_synced.id not in pending_ids


def test_sync_session_defaults_to_in_progress(institution_factory):
    institution = institution_factory()
    node = Node.objects.create(
        node_type=Node.NodeType.LOCAL, institution=institution, public_key="key"
    )

    session = SyncSession.objects.create(node=node)

    assert session.status == SyncSession.Status.IN_PROGRESS
    assert session.records_sent == 0
    assert session.records_received == 0
    assert session.errors == []
    assert session.finished_at is None
