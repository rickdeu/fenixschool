"""Tests for the personal language selector (issue #28, RF-I18N-02, RNF-LOC-07)."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def _create_user(institution, **kwargs):
    defaults = {
        "username": "aluno1",
        "email": "aluno1@escola.ao",
        "password": "senha-forte-123",
        "institution": institution,
        "profile": Profile.STUDENT,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def test_requires_login(client):
    response = client.post(
        reverse("accounts:set_preferred_language"), {"language": "umb"}
    )

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_post(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("accounts:set_preferred_language"))

    assert response.status_code == 405


def test_updates_only_the_current_users_own_preference(institution):
    user = _create_user(institution)
    other_user = _create_user(
        institution, username="aluno2", email="aluno2@escola.ao"
    )
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("accounts:set_preferred_language"), {"language": "umb"}
    )

    assert response.status_code == 302
    user.refresh_from_db()
    other_user.refresh_from_db()
    assert user.preferred_language == "umb"
    # RNF-LOC-07: no institution-wide setting -- other users are unaffected.
    assert other_user.preferred_language != "umb"


def test_invalid_language_code_is_ignored(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("accounts:set_preferred_language"), {"language": "xx-not-a-language"}
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.preferred_language != "xx-not-a-language"


def test_redirects_to_the_safe_next_url(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("accounts:set_preferred_language"),
        {"language": "kmb", "next": reverse("accounts:landing_placeholder")},
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:landing_placeholder")


def test_redirects_to_the_placeholder_when_next_is_missing(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("accounts:set_preferred_language"), {"language": "kmb"}
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:landing_placeholder")


def test_ignores_an_unsafe_open_redirect_next_url(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("accounts:set_preferred_language"),
        {"language": "kmb", "next": "https://evil.example/"},
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:landing_placeholder")


def test_language_selector_is_rendered_for_authenticated_users(institution):
    user = _create_user(institution)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("accounts:landing_placeholder"))

    content = response.content.decode()
    assert 'id="preferred-language-select"' in content
    assert "Umbundu" in content


def test_language_selector_is_absent_for_anonymous_users(client):
    response = client.get(reverse("accounts:login"))

    assert 'id="preferred-language-select"' not in response.content.decode()
