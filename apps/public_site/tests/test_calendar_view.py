"""Tests for the public school calendar (issue #104, docs/06-modulos-e-
funcionalidades.md §6.3)."""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.core.context import tenant_context
from apps.core.models import AcademicTerm, AcademicYear, Institution, NonTeachingDay

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def test_redirects_to_the_setup_wizard_when_no_institution_exists():
    response = Client().get(reverse("public_site:calendar"))

    assert response.status_code == 302
    assert response.url == reverse("core:setup_wizard")


def test_is_accessible_without_login(institution):
    response = Client().get(reverse("public_site:calendar"))

    assert response.status_code == 200


def test_shows_a_placeholder_without_a_current_academic_year(institution):
    content = Client().get(reverse("public_site:calendar")).content.decode()

    assert "Ainda não há nenhum ano lectivo corrente" in content


def test_shows_the_current_academic_years_designation_and_terms(institution):
    with tenant_context(institution.id):
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=academic_year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 1),
        )

    content = Client().get(reverse("public_site:calendar")).content.decode()

    assert "2026/2027" in content
    assert "1.º" in content


def test_ignores_a_non_current_academic_year(institution):
    with tenant_context(institution.id):
        AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2020/2021",
            start_date=date(2020, 2, 1),
            end_date=date(2020, 12, 15),
            is_current=False,
        )

    content = Client().get(reverse("public_site:calendar")).content.decode()

    assert "2020/2021" not in content
    assert "Ainda não há nenhum ano lectivo corrente" in content


def test_shows_non_teaching_days_within_the_current_academic_year(institution):
    with tenant_context(institution.id):
        AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )
        NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2026, 3, 8),
            description="Dia da Mulher",
            scope=NonTeachingDay.Scope.NATIONAL,
        )
        # Outside the current academic year's date range -- must not appear.
        NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2025, 1, 1),
            description="Ano Novo (ano lectivo anterior)",
            scope=NonTeachingDay.Scope.NATIONAL,
        )

    content = Client().get(reverse("public_site:calendar")).content.decode()

    assert "Dia da Mulher" in content
    assert "Ano Novo (ano lectivo anterior)" not in content


def test_never_shows_another_institutions_calendar_data(institution):
    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        AcademicYear.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="Ano Da Outra Escola",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )

    with tenant_context(institution.id):
        academic_year = (
            AcademicYear.all_objects.for_institution(institution.id)
            .filter(is_current=True)
            .first()
        )

    assert academic_year is None
