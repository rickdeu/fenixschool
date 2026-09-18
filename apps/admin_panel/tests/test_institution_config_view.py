"""Tests for the institution configuration panel (issue #114, RF-ADM-02)."""

import pytest
from django.contrib.auth.models import Group
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
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


def test_requires_login(client):
    response = client.get(reverse("admin_panel:institution_config"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_permission(institution):
    User.objects.create_user(
        username="prof1", institution=institution, profile=Profile.TEACHER, password="pw12345"
    )
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(reverse("admin_panel:institution_config"))

    assert response.status_code == 403


def test_lists_every_section_of_2_1(admin_client):
    response = admin_client.get(reverse("admin_panel:institution_config"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Dados da instituição" in content
    assert "Anos lectivos e períodos" in content
    assert "Ciclos lectivos" in content
    assert "Fórmula de cálculo de média" in content
    assert "Feriados e dias não lectivos" in content
    assert "Tabelas de preços" in content
    assert "Cópias de segurança" in content


def test_links_to_the_real_grading_formula_screen(admin_client):
    response = admin_client.get(reverse("admin_panel:institution_config"))

    assert reverse("admin_panel:grading_formula_config") in response.content.decode()


def test_links_to_the_dedicated_non_teaching_day_screen_not_django_admin(admin_client):
    response = admin_client.get(reverse("admin_panel:institution_config"))

    assert reverse("admin_panel:non_teaching_day_list") in response.content.decode()


def test_links_to_dedicated_screens_not_django_admin(admin_client):
    response = admin_client.get(reverse("admin_panel:institution_config"))

    content = response.content.decode()
    assert reverse("admin_panel:institution_edit") in content
    assert reverse("admin_panel:academic_year_list") in content
    assert reverse("admin_panel:academic_cycle_list") in content
    assert "/admin/core/" not in content


def test_price_tables_is_shown_as_unavailable_not_a_dead_link(admin_client):
    response = admin_client.get(reverse("admin_panel:institution_config"))

    sections = {s["title"]: s for s in response.context["sections"]}
    assert sections["Tabelas de preços"]["available"] is False
    assert sections["Tabelas de preços"]["url"] is None
