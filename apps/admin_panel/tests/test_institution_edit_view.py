"""Tests for the dedicated "Dados da instituição" screen (issue #114, RF-INST-01)."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

URL = reverse("admin_panel:institution_edit")


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


def test_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_permission(institution):
    User.objects.create_user(
        username="prof1", institution=institution, profile=Profile.TEACHER, password="pw12345"
    )
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(URL)

    assert response.status_code == 403


def test_shows_the_form_grouped_into_sections(admin_client):
    response = admin_client.get(URL)

    assert response.status_code == 200
    sections = {s["title"] for s in response.context["sections"]}
    assert sections == {
        "Identificação",
        "Morada",
        "Contactos",
        "Identidade visual",
        "Documentos oficiais",
        "Admissões",
    }


def test_updating_the_institutions_data(admin_client, institution):
    response = admin_client.post(
        URL,
        {
            "name": "Escola Piloto Actualizada",
            "tax_id": institution.tax_id,
            "ministry_of_education_code": institution.ministry_of_education_code,
            "description": "Uma nova apresentação.",
            "landline_phone": "222111222",
            "email": "geral@escola.ao",
            "website": "",
            "admission_exam_passing_score": institution.admission_exam_passing_score,
        },
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        institution.refresh_from_db()
    assert institution.name == "Escola Piloto Actualizada"
    assert institution.description == "Uma nova apresentação."
    assert institution.landline_phone == "222111222"


def test_invalid_submission_reopens_on_the_step_with_the_error(admin_client):
    response = admin_client.post(URL, {"name": "", "email": "nao-e-um-email"})

    assert response.status_code == 200
    # "name" lives in the "Identificação" section (step 1), "email" in
    # "Contactos" (step 3) -- the first one with an error wins.
    assert response.context["initial_step"] == 1
