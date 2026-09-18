"""Tests for `Enrollment` (issue #43, docs/05-modelo-de-dados.md §5.15, RF-MAT-05)."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Enrollment, Student

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def setup(institution, document_type):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        school_class = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )
        student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Ana",
            last_name="Silva",
            birth_date=date(2010, 5, 20),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="123456789LA000",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )
    return {
        "course": course,
        "cycle": cycle,
        "curricular_year": curricular_year,
        "academic_year": academic_year,
        "school_class": school_class,
        "student": student,
        "document_type": document_type,
    }


def _make_enrollment(institution, setup, **overrides):
    fields = {
        "institution": institution,
        "origin_node_id": _origin(),
        "student": setup["student"],
        "course": setup["course"],
        "academic_year": setup["academic_year"],
        "school_class": setup["school_class"],
        "cycle": setup["cycle"],
        "curricular_year": setup["curricular_year"],
        "presented_document_type": setup["document_type"],
        "presented_document_number": "123456789LA000",
        "document_issue_date": date(2020, 1, 1),
        "document_issue_place": "Nacional - Luanda",
    }
    fields.update(overrides)
    return Enrollment.objects.create(**fields)


def test_enrollment_number_is_assigned_sequentially_per_institution_and_year(institution, setup):
    with tenant_context(institution.id):
        first = _make_enrollment(institution, setup)
        second = _make_enrollment(institution, setup)

    assert first.enrollment_number == 1
    assert second.enrollment_number == 2


def test_enrollment_number_resets_per_academic_year(institution, setup, document_type):
    with tenant_context(institution.id):
        first = _make_enrollment(institution, setup)

        other_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2027/2028",
            start_date=date(2027, 2, 1),
            end_date=date(2027, 12, 15),
        )
        other_class = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=other_year,
            course=setup["course"],
            curricular_year=setup["curricular_year"],
            shift=SchoolClass.Shift.MORNING,
        )
        second = _make_enrollment(
            institution, setup, academic_year=other_year, school_class=other_class
        )

    assert first.enrollment_number == 1
    assert second.enrollment_number == 1


def test_enrollment_defaults_to_pending_status(institution, setup):
    with tenant_context(institution.id):
        enrollment = _make_enrollment(institution, setup)

    assert enrollment.status == Enrollment.Status.PENDING


def test_enrollment_can_reference_a_previous_enrollment_for_repeating_students(institution, setup):
    with tenant_context(institution.id):
        first = _make_enrollment(institution, setup)
        second = _make_enrollment(institution, setup, is_repeating=True, previous_enrollment=first)

    assert second.previous_enrollment == first
    assert second.is_repeating


def test_enrollment_course_must_belong_to_the_same_institution(institution, setup):
    other_institution = type(institution).objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        other_department = Department.objects.create(
            institution=other_institution, origin_node_id=_origin(), name="Outro"
        )
        other_cycle = AcademicCycle.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )
        foreign_course = Course.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            code="FOR",
            name="Foreign",
            created_on=date(2020, 1, 1),
            department=other_department,
            cycle=other_cycle,
            duration_years=4,
        )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        _make_enrollment(institution, setup, course=foreign_course)


def test_enrollment_presented_document_type_needs_no_institution_check(institution, setup):
    """Regression guard: `presented_document_type` is shared national
    reference data (like `Student.document_type`) -- must not be validated
    against `institution`."""
    with tenant_context(institution.id):
        enrollment = _make_enrollment(institution, setup)

    assert enrollment.presented_document_type == setup["document_type"]
