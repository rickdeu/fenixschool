"""Tests for `EnrollmentAdmin`/`StudentGuardianAdmin` -- explicit
alphabetical-by-student ordering, per the user's own request."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Guardian, Student
from apps.enrollment.services import enroll_student, register_student

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


def _make_enrollment(institution, document_type, *, first_name, last_name, doc_suffix, order):
    from apps.academic.models import Course, CurricularYear, Department, SchoolClass

    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=order
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code=f"CUR-{doc_suffix}",
            name="Curso Teste",
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
            code=f"10A-{doc_suffix}",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number=f"ENC-{doc_suffix}",
        )
        student = register_student(
            institution=institution,
            document_type=document_type,
            document_number=f"AL-{doc_suffix}",
            guardian_consent_given_by=guardian,
            origin_node_id=_origin(),
            first_name=first_name,
            last_name=last_name,
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )
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


def test_enrollment_changelist_lists_students_alphabetically(
    admin_client, institution, document_type
):
    # "Zeferino" enrolled first (would sort last by enrollment_number/date),
    # "Ana" enrolled second -- the default `Enrollment.Meta.ordering` alone
    # would show Zeferino before Ana; alphabetically (by first name), Ana
    # must come first.
    _make_enrollment(
        institution,
        document_type,
        first_name="Zeferino",
        last_name="Alberto",
        doc_suffix="1",
        order=1,
    )
    _make_enrollment(
        institution, document_type, first_name="Ana", last_name="Zulu", doc_suffix="2", order=2
    )

    response = admin_client.get(reverse("admin:enrollment_enrollment_changelist"))

    content = response.content.decode()
    assert content.index("Ana") < content.index("Zeferino")
