"""Tests for session idle-timeout by profile (issue #27,
docs/09-seguranca-e-privacidade.md §9.2)."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profile, User
from apps.accounts.services import get_session_timeout_seconds

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("profile", "expected_minutes"),
    [
        (Profile.SUPER_ADMIN, 15),
        (Profile.INSTITUTION_ADMIN, 15),
        (Profile.FINANCE, 15),
        (Profile.SECRETARY, 15),
        (Profile.PEDAGOGICAL_DIRECTION, 30),
        (Profile.HR, 30),
        (Profile.HOMEROOM_TEACHER, 30),
        (Profile.LIBRARY, 30),
        (Profile.TEACHER, 60),
        (Profile.GUARDIAN, 60),
        (Profile.STUDENT, 60),
    ],
)
def test_session_timeout_is_configured_per_profile(profile, expected_minutes):
    user = User(profile=profile)

    assert get_session_timeout_seconds(user) == expected_minutes * 60


def test_admin_and_finance_get_a_shorter_timeout_than_teachers():
    """docs/09-seguranca-e-privacidade.md §9.2's own reasoning, asserted
    directly: higher-risk/shared-workstation profiles must never end up
    with a *longer* idle window than an ordinary teacher's personal-device
    login."""
    admin_timeout = get_session_timeout_seconds(User(profile=Profile.INSTITUTION_ADMIN))
    finance_timeout = get_session_timeout_seconds(User(profile=Profile.FINANCE))
    secretary_timeout = get_session_timeout_seconds(User(profile=Profile.SECRETARY))
    teacher_timeout = get_session_timeout_seconds(User(profile=Profile.TEACHER))

    assert admin_timeout < teacher_timeout
    assert finance_timeout < teacher_timeout
    assert secretary_timeout < teacher_timeout


def test_unknown_profile_falls_back_to_the_default_timeout():
    user = User(profile="does-not-exist")

    assert get_session_timeout_seconds(user) == settings.DEFAULT_SESSION_TIMEOUT_MINUTES * 60


def test_middleware_sets_the_sessions_expiry_on_an_authenticated_request():
    User.objects.create_user(username="prof1", profile=Profile.TEACHER, password="pw12345")
    client = Client()
    client.login(username="prof1", password="pw12345")

    client.get(reverse("accounts:landing_placeholder"))

    # `get_expiry_age()` returns *approximately* the configured value (a
    # couple of seconds may have elapsed since the request) -- allow a
    # small margin instead of an exact match.
    expected = settings.SESSION_TIMEOUT_MINUTES_BY_PROFILE[Profile.TEACHER] * 60
    assert abs(client.session.get_expiry_age() - expected) < 5


def test_middleware_leaves_an_anonymous_sessions_expiry_untouched(client):
    default_age = client.session.get_expiry_age()

    client.get(reverse("accounts:login"))

    assert client.session.get_expiry_age() == default_age


def test_an_idle_session_actually_logs_the_user_out():
    """Functional proof, not just a unit-level assertion on the setting:
    simulating a session past its expiry means the *next* request is
    treated as anonymous, exactly like closing and reopening the browser
    after the idle window (issue #27's acceptance criterion)."""
    User.objects.create_user(username="prof2", profile=Profile.TEACHER, password="pw12345")
    client = Client()
    client.login(username="prof2", password="pw12345")

    session = client.session
    session.set_expiry(timezone.now() - timedelta(seconds=1))
    session.save()

    response = client.get(reverse("accounts:landing_placeholder"), follow=True)

    assert response.redirect_chain
    assert response.redirect_chain[0][0].startswith(reverse("accounts:login"))
