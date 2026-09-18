"""Tests for the user management screens (issue #113, RF-ADM-01)."""

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
    )
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client, admin


# -- user_list_view -----------------------------------------------------------


def test_list_requires_login(client):
    response = client.get(reverse("admin_panel:user_list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_list_requires_permission(institution):
    User.objects.create_user(
        username="prof1", institution=institution, profile=Profile.TEACHER, password="pw12345"
    )
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(reverse("admin_panel:user_list"))

    assert response.status_code == 403


def test_list_only_shows_this_institutions_users(admin_client, institution):
    from apps.core.factories import InstitutionFactory

    client, admin = admin_client
    other_institution = InstitutionFactory()
    User.objects.create_user(
        username="other_school_user",
        institution=other_institution,
        profile=Profile.TEACHER,
        password="pw12345",
    )

    response = client.get(reverse("admin_panel:user_list"))

    content = response.content.decode()
    assert admin.username in content
    assert "other_school_user" not in content


# -- user_create_view -----------------------------------------------------------


def test_create_view_requires_permission(institution):
    User.objects.create_user(
        username="prof2", institution=institution, profile=Profile.TEACHER, password="pw12345"
    )
    client = Client()
    client.login(username="prof2", password="pw12345")

    response = client.get(reverse("admin_panel:user_create"))

    assert response.status_code == 403


def test_super_admin_is_not_an_assignable_profile_choice(admin_client):
    client, _admin = admin_client

    response = client.get(reverse("admin_panel:user_create"))

    assert "super_admin" not in response.content.decode()


def test_creates_a_user_scoped_to_the_creators_institution(admin_client, institution):
    client, admin = admin_client

    response = client.post(
        reverse("admin_panel:user_create"),
        {
            "username": "novaprofessora",
            "first_name": "Ana",
            "last_name": "Silva",
            "email": "ana@escola.ao",
            "phone": "",
            "profile": Profile.TEACHER,
            "password": "uma-password-bastante-forte-123",
            "password_confirmation": "uma-password-bastante-forte-123",
        },
    )

    assert response.status_code == 302
    created = User.objects.get(username="novaprofessora")
    assert created.institution == institution
    assert created.created_by == admin
    assert created.check_password("uma-password-bastante-forte-123")
    assert list(created.groups.values_list("name", flat=True)) == ["Docente"]


def test_rejects_mismatched_passwords(admin_client):
    client, _admin = admin_client

    response = client.post(
        reverse("admin_panel:user_create"),
        {
            "username": "novoutilizador",
            "profile": Profile.TEACHER,
            "password": "uma-password-bastante-forte-123",
            "password_confirmation": "outra-password-diferente-456",
        },
    )

    assert response.status_code == 200
    assert not User.objects.filter(username="novoutilizador").exists()


def test_rejects_a_weak_password(admin_client):
    client, _admin = admin_client

    response = client.post(
        reverse("admin_panel:user_create"),
        {
            "username": "novoutilizador2",
            "profile": Profile.TEACHER,
            "password": "123",
            "password_confirmation": "123",
        },
    )

    assert response.status_code == 200
    assert not User.objects.filter(username="novoutilizador2").exists()


def test_rejects_a_duplicate_username(admin_client):
    client, admin = admin_client

    response = client.post(
        reverse("admin_panel:user_create"),
        {
            "username": admin.username,
            "profile": Profile.TEACHER,
            "password": "uma-password-bastante-forte-123",
            "password_confirmation": "uma-password-bastante-forte-123",
        },
    )

    assert response.status_code == 200
    assert User.objects.filter(username=admin.username).count() == 1


# -- user_edit_view -----------------------------------------------------------


def test_cannot_edit_a_user_from_another_institution(admin_client):
    from apps.core.factories import InstitutionFactory

    client, _admin = admin_client
    other_institution = InstitutionFactory()
    other_user = User.objects.create_user(
        username="outro", institution=other_institution, profile=Profile.TEACHER
    )

    response = client.get(reverse("admin_panel:user_edit", args=[other_user.id]))

    assert response.status_code == 404


def test_edits_a_users_profile_and_re_syncs_their_group(admin_client, institution):
    client, _admin = admin_client
    target = User.objects.create_user(
        username="funcionario1",
        institution=institution,
        profile=Profile.TEACHER,
        password="pw12345",
    )
    assert list(target.groups.values_list("name", flat=True)) == ["Docente"]

    response = client.post(
        reverse("admin_panel:user_edit", args=[target.id]),
        {
            "first_name": "Novo",
            "last_name": "Nome",
            "email": "",
            "phone": "",
            "profile": Profile.SECRETARY,
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    target.refresh_from_db()
    assert target.profile == Profile.SECRETARY
    assert list(target.groups.values_list("name", flat=True)) == ["Secretaria Escolar"]


def test_deactivating_a_user_through_the_form_takes_effect(admin_client, institution):
    client, _admin = admin_client
    target = User.objects.create_user(
        username="funcionario2", institution=institution, profile=Profile.TEACHER
    )

    client.post(
        reverse("admin_panel:user_edit", args=[target.id]),
        {
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "profile": Profile.TEACHER,
            "is_active": "",
        },
    )

    target.refresh_from_db()
    assert target.is_active is False
