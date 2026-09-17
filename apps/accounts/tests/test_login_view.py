"""Tests for the login view/template (issue #24)."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def test_login_form_has_no_institution_field(client):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert "institution" not in response.content.decode()
    assert "Email ou telefone" in response.content.decode()


def test_successful_login_redirects_a_staff_profile_to_the_admin(institution):
    User.objects.create_user(
        username="gestor",
        email="gestor@escola.ao",
        password="senha-forte-123",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        is_staff=True,
    )

    client = Client()
    response = client.post(
        reverse("accounts:login"),
        {"username": "gestor@escola.ao", "password": "senha-forte-123"},
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")


def test_successful_login_redirects_a_portal_profile_to_the_placeholder(institution):
    User.objects.create_user(
        username="aluno1",
        email="aluno1@escola.ao",
        password="senha-forte-123",
        institution=institution,
        profile=Profile.STUDENT,
    )

    client = Client()
    response = client.post(
        reverse("accounts:login"),
        {"username": "aluno1@escola.ao", "password": "senha-forte-123"},
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:landing_placeholder")


def test_invalid_credentials_show_a_clear_portuguese_error(client):
    response = client.post(
        reverse("accounts:login"),
        {"username": "ninguem@escola.ao", "password": "errada"},
    )

    assert response.status_code == 200
    assert "Credenciais inválidas" in response.content.decode()


def test_landing_placeholder_requires_login(client):
    response = client.get(reverse("accounts:landing_placeholder"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
