"""Tests for the public institutional page (issue #100, RF-PUB-01)."""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, Department
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, Institution

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def test_redirects_to_the_setup_wizard_when_no_institution_exists():
    response = Client().get(reverse("public_site:home"))

    assert response.status_code == 302
    assert response.url == reverse("core:setup_wizard")


def test_is_accessible_without_login_and_shows_the_institution(institution):
    response = Client().get(reverse("public_site:home"))

    assert response.status_code == 200
    assert institution.name in response.content.decode()


def test_shows_the_institutions_description_when_set(institution):
    institution.description = "Uma escola de referência em Luanda."
    institution.save(update_fields=["description"])

    response = Client().get(reverse("public_site:home"))

    assert "Uma escola de referência em Luanda." in response.content.decode()


def test_shows_the_institutions_contacts(institution):
    institution.email = "geral@escola.ao"
    institution.landline_phone = "222000000"
    institution.save(update_fields=["email", "landline_phone"])

    content = Client().get(reverse("public_site:home")).content.decode()

    assert "geral@escola.ao" in content
    assert "222000000" in content


def test_shows_the_institutions_real_courses(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )

    content = Client().get(reverse("public_site:home")).content.decode()

    assert "Informática" in content


def test_shows_a_placeholder_when_there_are_no_courses_yet(institution):
    content = Client().get(reverse("public_site:home")).content.decode()

    assert "Ainda não há cursos publicados" in content


def test_the_course_query_never_leaks_another_institutions_courses(institution):
    """The view's `Course.all_objects.for_institution(...)` call must never
    return a course belonging to some other institution -- checked directly
    against the queryset (rather than through `home_view`, whose "which
    institution is THE one this node shows" resolution is deliberately
    naive -- `Institution.objects.first()` -- since this MVP only ever
    hosts one at a time; that's a separate concern from tenant isolation
    itself, which is what this test is about)."""
    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Curso Desta Escola",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
    with tenant_context(other_institution.id):
        other_department = Department.objects.create(
            institution=other_institution, origin_node_id=_origin(), name="Letras"
        )
        other_cycle = AcademicCycle.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )
        Course.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            code="LET",
            name="Curso Da Outra Escola",
            created_on=date(2020, 1, 1),
            department=other_department,
            cycle=other_cycle,
            duration_years=4,
        )

    course_names = list(
        Course.all_objects.for_institution(institution.id).values_list("name", flat=True)
    )

    assert course_names == ["Curso Desta Escola"]
