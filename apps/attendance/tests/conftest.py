"""Shared fixtures for `apps.attendance` tests."""

import uuid
from datetime import date

import pytest

from apps.academic.models import Course, Department, SchoolClass, Subject
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType


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
    from apps.academic.models import CurricularYear

    with tenant_context(institution.id):
        return CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )


@pytest.fixture
def subject(institution, course, curricular_year, cycle):
    with tenant_context(institution.id):
        return Subject.objects.create(
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


@pytest.fixture
def academic_year(institution):
    with tenant_context(institution.id):
        return AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )


@pytest.fixture
def school_class(institution, academic_year, course, curricular_year):
    with tenant_context(institution.id):
        return SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def student(institution, document_type):
    from apps.enrollment.models import Guardian, Student

    with tenant_context(institution.id):
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-1",
        )
        return Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Yolene",
            last_name="Hangalo",
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="005LA00123",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )


@pytest.fixture
def enrollment(
    institution, student, school_class, course, academic_year, cycle, curricular_year, document_type
):
    from apps.enrollment.services import enroll_student

    with tenant_context(institution.id):
        return enroll_student(
            institution=institution,
            student=student,
            school_class=school_class,
            origin_node_id=_origin(),
            course=course,
            academic_year=academic_year,
            cycle=cycle,
            curricular_year=curricular_year,
            presented_document_type=document_type,
            presented_document_number=student.document_number,
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )


@pytest.fixture
def teacher(institution, user_factory):
    from apps.accounts.models import Profile

    return user_factory(username="professor1", profile=Profile.TEACHER, institution=institution)


@pytest.fixture
def room(institution):
    from apps.academic.models import Room

    with tenant_context(institution.id):
        return Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=30
        )


@pytest.fixture
def schedule(institution, school_class, subject, teacher, room):
    from datetime import time

    from apps.academic.models import Schedule

    with tenant_context(institution.id):
        return Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=teacher,
        )
