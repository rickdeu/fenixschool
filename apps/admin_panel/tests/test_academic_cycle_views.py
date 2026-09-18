"""Tests for the dedicated "Ciclos lectivos" screen (issue #16, RF-INST-05)."""

import uuid

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin_panel:academic_cycle_list")
CREATE_URL = reverse("admin_panel:academic_cycle_create")


def _origin():
    return uuid.uuid4()


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
    response = client.get(LIST_URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_lists_the_institutions_cycles(admin_client, institution):
    with tenant_context(institution.id):
        AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )

    response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    assert "1.º Ciclo" in response.content.decode()


def test_create_a_cycle(admin_client, institution):
    response = admin_client.post(
        CREATE_URL, {"designation": "2.º Ciclo", "order": 2}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        cycle = AcademicCycle.objects.get(designation="2.º Ciclo")
    assert cycle.order == 2
    assert cycle.institution_id == institution.id


def test_duplicate_order_is_rejected_with_a_clear_message(admin_client, institution):
    with tenant_context(institution.id):
        AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )

    response = admin_client.post(CREATE_URL, {"designation": "Outro Ciclo", "order": 1})

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not AcademicCycle.objects.filter(designation="Outro Ciclo").exists()


def test_edit_a_cycle(admin_client, institution):
    with tenant_context(institution.id):
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )

    response = admin_client.post(
        reverse("admin_panel:academic_cycle_edit", args=[cycle.pk]),
        {"designation": "1.º Ciclo (renomeado)", "order": 1},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        cycle.refresh_from_db()
    assert cycle.designation == "1.º Ciclo (renomeado)"


def test_delete_a_cycle(admin_client, institution):
    with tenant_context(institution.id):
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )

    response = admin_client.post(
        reverse("admin_panel:academic_cycle_edit", args=[cycle.pk]), {"delete": "1"}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not AcademicCycle.objects.filter(pk=cycle.pk).exists()


def test_cannot_edit_another_institutions_cycle(admin_client):
    from apps.core.models import Institution

    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        cycle = AcademicCycle.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )

    response = admin_client.get(reverse("admin_panel:academic_cycle_edit", args=[cycle.pk]))

    assert response.status_code == 404
