"""Tests for the `create_dev_superuser` management command (local dev convenience,
see scripts/entrypoint.sh)."""

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True)
def test_creates_the_root_superuser_when_debug_is_on():
    call_command("create_dev_superuser")

    user = User.objects.get(username="root")
    assert user.check_password("root")
    assert user.is_staff
    assert user.is_superuser
    assert user.profile == Profile.SUPER_ADMIN


@override_settings(DEBUG=True)
def test_is_idempotent():
    call_command("create_dev_superuser")
    call_command("create_dev_superuser")

    assert User.objects.filter(username="root").count() == 1


@override_settings(DEBUG=False)
def test_does_nothing_when_debug_is_off():
    call_command("create_dev_superuser")

    assert not User.objects.filter(username="root").exists()
