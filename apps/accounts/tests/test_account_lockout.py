"""Tests for progressive account lockout (issue #26, RNF-SEC-02,
docs/09-seguranca-e-privacidade.md §9.2)."""

from datetime import timedelta

import pytest
from django.contrib import admin
from django.contrib.auth import authenticate
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.admin import CustomUserAdmin
from apps.accounts.models import User
from apps.accounts.services import (
    MAX_FAILED_LOGIN_ATTEMPTS,
    lockout_duration_minutes,
    register_failed_login,
    reset_lockout_state,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="joao", email="joao@escola.ao", password="senha-forte-123"
    )


def test_lockout_duration_is_progressive_and_capped():
    durations = [lockout_duration_minutes(n) for n in range(10)]

    assert durations[0] == 1
    assert durations[1] == 2
    assert durations[2] == 4
    # Strictly increasing until the cap.
    assert all(b >= a for a, b in zip(durations, durations[1:], strict=True))
    assert durations[-1] <= 60


def test_account_is_locked_after_the_max_failed_attempts(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        authenticate(username="joao@escola.ao", password="wrong")

    user.refresh_from_db()
    assert user.is_locked is True
    assert user.lockout_count == 1
    assert user.failed_login_attempts == 0


def test_fewer_than_the_threshold_does_not_lock_the_account(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
        authenticate(username="joao@escola.ao", password="wrong")

    user.refresh_from_db()
    assert user.is_locked is False
    assert user.failed_login_attempts == MAX_FAILED_LOGIN_ATTEMPTS - 1


def test_a_locked_account_cannot_authenticate_even_with_the_correct_password(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        authenticate(username="joao@escola.ao", password="wrong")

    assert authenticate(username="joao@escola.ao", password="senha-forte-123") is None


def test_repeated_attempts_during_an_active_lockout_do_not_extend_it(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        authenticate(username="joao@escola.ao", password="wrong")
    user.refresh_from_db()
    first_locked_until = user.locked_until

    for _ in range(3):
        authenticate(username="joao@escola.ao", password="wrong")
    user.refresh_from_db()

    assert user.locked_until == first_locked_until
    assert user.lockout_count == 1


def test_a_second_lockout_lasts_longer_than_the_first(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        register_failed_login(user)
    user.refresh_from_db()
    first_duration = user.locked_until - timezone.now()

    # Simulate the first lockout having already expired.
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["locked_until"])

    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        register_failed_login(user)
    user.refresh_from_db()
    second_duration = user.locked_until - timezone.now()

    assert user.lockout_count == 2
    assert second_duration > first_duration


def test_a_successful_login_resets_the_lockout_state(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
        authenticate(username="joao@escola.ao", password="wrong")
    user.refresh_from_db()
    assert user.failed_login_attempts == MAX_FAILED_LOGIN_ATTEMPTS - 1

    client = Client()
    assert client.login(username="joao@escola.ao", password="senha-forte-123")

    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert user.lockout_count == 0


def test_reset_lockout_state_is_a_no_op_when_nothing_is_set(user):
    # Doesn't raise, doesn't hit the database unnecessarily.
    reset_lockout_state(user)


def test_administrator_can_unlock_an_account_manually(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        register_failed_login(user)
    user.refresh_from_db()
    assert user.is_locked is True

    user.unlock()

    assert user.is_locked is False
    assert user.failed_login_attempts == 0
    assert user.lockout_count == 0
    assert authenticate(username="joao@escola.ao", password="senha-forte-123") == user


def test_admin_unlock_action_unlocks_every_selected_user(rf, user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        register_failed_login(user)
    user.refresh_from_db()
    assert user.is_locked is True

    admin_instance = CustomUserAdmin(User, admin_site=admin.site)
    request = rf.post("/admin/accounts/user/")
    request.session = {}
    request._messages = FallbackStorage(request)
    admin_instance.unlock_accounts(request, User.objects.filter(pk=user.pk))

    user.refresh_from_db()
    assert user.is_locked is False


def test_username_based_login_is_also_subject_to_lockout():
    """The Django Admin's own login screen authenticates by `username`, via
    `LockoutAwareModelBackend` -- must be under the same lockout, not a
    loophole around it."""
    User.objects.create_user(username="admin_user", password="senha-forte-123")

    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        authenticate(username="admin_user", password="wrong")

    assert authenticate(username="admin_user", password="senha-forte-123") is None


def test_login_view_shows_a_clear_account_locked_message(user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        authenticate(username="joao@escola.ao", password="wrong")

    response = Client().post(
        reverse("accounts:login"), {"username": "joao@escola.ao", "password": "senha-forte-123"}
    )

    assert response.status_code == 200
    assert "temporariamente bloqueada" in response.content.decode()


def test_argon2_is_the_configured_default_hasher():
    """Checked against `config.settings.base` directly, not the active
    Django settings: `config.settings.test` deliberately overrides
    `PASSWORD_HASHERS` with a fast, insecure hasher (MD5) so the test suite
    itself doesn't pay Argon2's (deliberately expensive) cost on every user
    created -- see that module's own docstring. That override is itself the
    reason this can't be asserted via `User.objects.create_user()` here.
    """
    from config.settings import base as base_settings

    assert base_settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"
