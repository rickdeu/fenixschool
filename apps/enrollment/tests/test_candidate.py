"""Tests for `Candidate` (issue #42, docs/05-modelo-de-dados.md §5.14, RF-MAT-10)."""

import uuid
from datetime import date

import pytest

from apps.academic.models import Course, Department
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle
from apps.enrollment.models import Candidate

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def course(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        return Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )


def test_candidate_defaults_to_pending(institution, course):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            desired_course=course,
            contact="923000000",
        )

    assert candidate.status == Candidate.Status.PENDING
    assert str(candidate) == "Pedro Neto"


def test_student_defaults_prefills_name_and_birth_date(institution, course):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            desired_course=course,
            contact="923000000",
        )

    defaults = candidate.student_defaults()

    assert defaults == {
        "first_name": "Pedro",
        "last_name": "Neto",
        "birth_date": date(2011, 3, 15),
    }
