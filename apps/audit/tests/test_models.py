"""Tests for `audit.AuditLogEntry` itself -- issue #140, RNF-AUD-01/03."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Profile, User
from apps.audit.models import AuditLogEntry

pytestmark = pytest.mark.django_db


def test_str_includes_action_entity_and_id():
    entry = AuditLogEntry.objects.create(
        action=AuditLogEntry.Action.CREATE, entity="accounts.User", entity_id="123"
    )

    assert "accounts.User" in str(entry)
    assert "123" in str(entry)


def test_entries_are_immutable_cannot_be_updated():
    entry = AuditLogEntry.objects.create(
        action=AuditLogEntry.Action.CREATE, entity="accounts.User", entity_id="123"
    )

    entry.entity_id = "456"
    with pytest.raises(ValidationError):
        entry.save()


def test_entries_are_immutable_cannot_be_deleted():
    entry = AuditLogEntry.objects.create(
        action=AuditLogEntry.Action.CREATE, entity="accounts.User", entity_id="123"
    )

    with pytest.raises(ValidationError):
        entry.delete()

    assert AuditLogEntry.objects.filter(pk=entry.pk).exists()


def test_user_deletion_does_not_delete_the_entry():
    """SET_NULL, not CASCADE -- the audit trail must outlive the user it's
    about."""
    user = User.objects.create_user(username="temp", profile=Profile.TEACHER)
    entry = AuditLogEntry.objects.create(
        user=user,
        action=AuditLogEntry.Action.CREATE,
        entity="accounts.User",
        entity_id=str(user.pk),
    )

    user.delete()
    entry.refresh_from_db()

    assert entry.user is None
