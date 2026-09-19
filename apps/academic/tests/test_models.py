"""Tests for the academic curriculum models (issues #30-#35, docs/05-modelo-de-dados.md
§5.4-§5.9)."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academic.models import (
    Course,
    CurricularYear,
    Department,
    Room,
    SchoolClass,
    Subject,
)
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def cycle(institution):
    with tenant_context(institution.id):
        return AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )


@pytest.fixture
def department(institution):
    with tenant_context(institution.id):
        return Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )


@pytest.fixture
def course(institution, department, cycle):
    with tenant_context(institution.id):
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


@pytest.fixture
def curricular_year(institution, course):
    with tenant_context(institution.id):
        return CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )


def test_department_str_is_its_name(department):
    assert str(department) == "Ciências"


def test_course_code_is_unique_per_institution(institution, department, cycle):
    with tenant_context(institution.id):
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

        # Course.save() runs full_clean(), so this is caught as a
        # ValidationError before it ever reaches the database.
        with pytest.raises(ValidationError):
            Course.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                code="INF",
                name="Outro Curso",
                created_on=date(2021, 1, 1),
                department=department,
                cycle=cycle,
                duration_years=4,
            )


def test_course_cycle_must_belong_to_the_same_institution(institution, department):
    other_institution_cycle_owner = type(institution).objects.create(name="Outra Escola")
    with tenant_context(other_institution_cycle_owner.id):
        foreign_cycle = AcademicCycle.objects.create(
            institution=other_institution_cycle_owner,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=foreign_cycle,
            duration_years=4,
        )


def test_curricular_year_str(curricular_year):
    assert "1.º Ano" in str(curricular_year)
    assert "10.ª classe" in str(curricular_year)


def test_curricular_year_number_is_unique_per_course(institution, course):
    with tenant_context(institution.id):
        CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )

        with transaction.atomic(), pytest.raises(IntegrityError):
            CurricularYear.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                course=course,
                number=1,
                equivalent_grade="10.ª classe (repetente)",
            )


def test_subject_curricular_year_must_belong_to_its_own_course(institution, department, cycle):
    with tenant_context(institution.id):
        course_a = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        course_b = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="ECO",
            name="Economia",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        year_of_b = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course_b,
            number=1,
            equivalent_grade="10.ª classe",
        )

        with pytest.raises(ValidationError):
            Subject.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                code="MAT",
                name="Matemática",
                created_on=date(2020, 1, 1),
                course=course_a,
                curricular_year=year_of_b,
                cycle=cycle,
                subject_type=Subject.SubjectType.MANDATORY,
                weekly_hours=4,
            )


def test_subject_is_created_successfully_with_valid_relations(
    institution, course, curricular_year, cycle
):
    with tenant_context(institution.id):
        subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT",
            name="Matemática",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )

    assert str(subject) == "Matemática"


def test_room_str_is_its_designation(institution):
    with tenant_context(institution.id):
        room = Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=40
        )

    assert str(room) == "Sala 1"


def test_school_class_defaults_max_enrollment_to_36(institution, course, curricular_year):
    with tenant_context(institution.id):
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

    assert school_class.max_enrollment == 36
    assert school_class.exceeds_legal_enrollment_ceiling is False


def test_school_class_flags_max_enrollment_above_the_legal_ceiling(
    institution, course, curricular_year
):
    """Issue #174 (RF-CURR-05): "aviso, não bloqueio automático" -- um
    valor acima do tecto legal (45, Decreto Presidencial 162/23) é aceite
    (nunca levanta `ValidationError`), só fica sinalizado."""
    with tenant_context(institution.id):
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
            max_enrollment=50,
        )

    assert school_class.exceeds_legal_enrollment_ceiling is True


def test_school_class_code_is_unique_per_academic_year(institution, course, curricular_year):
    with tenant_context(institution.id):
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )

        # SchoolClass.save() runs full_clean(), so this is caught as a
        # ValidationError before it ever reaches the database.
        with pytest.raises(ValidationError):
            SchoolClass.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                code="10A",
                designation="10.ª A (Tarde)",
                academic_year=academic_year,
                course=course,
                curricular_year=curricular_year,
                shift=SchoolClass.Shift.AFTERNOON,
            )


def test_school_class_curricular_year_must_belong_to_its_own_course(institution, department, cycle):
    with tenant_context(institution.id):
        course_a = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        course_b = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="ECO",
            name="Economia",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        year_of_b = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course_b,
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

        with pytest.raises(ValidationError):
            SchoolClass.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                code="10A",
                designation="10.ª A",
                academic_year=academic_year,
                course=course_a,
                curricular_year=year_of_b,
                shift=SchoolClass.Shift.MORNING,
            )
