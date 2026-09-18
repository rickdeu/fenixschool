"""Tests for the dedicated "Anos lectivos e trimestres" screen (issue #16,
RF-INST-03/04)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicTerm, AcademicYear

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin_panel:academic_year_list")
CREATE_URL = reverse("admin_panel:academic_year_create")


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


def test_create_an_academic_year(admin_client, institution):
    response = admin_client.post(
        CREATE_URL,
        {"designation": "2026/2027", "start_date": "2026-02-01", "end_date": "2026-12-15"},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        year = AcademicYear.objects.get(designation="2026/2027")
    assert year.institution_id == institution.id
    assert year.is_current is False


def test_invalid_date_range_is_rejected_with_a_clear_message(admin_client):
    response = admin_client.post(
        CREATE_URL,
        {"designation": "2026/2027", "start_date": "2026-12-15", "end_date": "2026-02-01"},
    )

    assert response.status_code == 200
    assert "posterior" in response.content.decode()


def test_marking_a_year_as_current_unmarks_the_previous_one(admin_client, institution):
    with tenant_context(institution.id):
        old_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2025/2026",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 12, 15),
            is_current=True,
        )
        new_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    response = admin_client.post(LIST_URL, {"mark_current": str(new_year.pk)}, follow=True)

    assert response.status_code == 200
    with tenant_context(institution.id):
        old_year.refresh_from_db()
        new_year.refresh_from_db()
    assert old_year.is_current is False
    assert new_year.is_current is True


def test_delete_an_academic_year_cascades_its_terms(admin_client, institution):
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

    response = admin_client.post(
        reverse("admin_panel:academic_year_edit", args=[year.pk]), {"delete": "1"}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not AcademicYear.objects.filter(pk=year.pk).exists()
        assert not AcademicTerm.objects.filter(academic_year_id=year.pk).exists()


def test_create_a_term_within_the_year(admin_client, institution):
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    response = admin_client.post(
        reverse("admin_panel:academic_term_create", args=[year.pk]),
        {"number": 1, "start_date": "2026-02-01", "end_date": "2026-05-31"},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        term = AcademicTerm.objects.get(academic_year=year, number=1)
    assert term.institution_id == institution.id


def test_a_term_outside_the_years_dates_is_rejected(admin_client, institution):
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    response = admin_client.post(
        reverse("admin_panel:academic_term_create", args=[year.pk]),
        {"number": 1, "start_date": "2026-01-01", "end_date": "2026-05-31"},
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not AcademicTerm.objects.filter(academic_year=year).exists()


def test_edit_and_delete_a_term(admin_client, institution):
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        term = AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

    edit_url = reverse("admin_panel:academic_term_edit", args=[term.pk])
    response = admin_client.post(
        edit_url,
        {"number": 1, "start_date": "2026-02-01", "end_date": "2026-06-15"},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        term.refresh_from_db()
    assert term.end_date == date(2026, 6, 15)

    response = admin_client.post(edit_url, {"delete": "1"}, follow=True)

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert not AcademicTerm.objects.filter(pk=term.pk).exists()


def test_cannot_edit_another_institutions_year(admin_client):
    from apps.core.models import Institution

    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        year = AcademicYear.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    response = admin_client.get(reverse("admin_panel:academic_year_edit", args=[year.pk]))

    assert response.status_code == 404
