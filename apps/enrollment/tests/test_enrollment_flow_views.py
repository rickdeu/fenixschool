"""Tests for the Matrícula views (issue #47, RF-MAT-04/05/06/07, docs/06-
modulos-e-funcionalidades.md §6.4)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Enrollment, Guardian, Student

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def secretary_client(institution):
    secretary = User.objects.create_user(
        username="secretaria1",
        institution=institution,
        profile=Profile.SECRETARY,
        password="senha-forte-123",
    )
    secretary.groups.add(Group.objects.get(name="Secretaria Escolar"))
    client = Client()
    client.login(username="secretaria1", password="senha-forte-123")
    return client


@pytest.fixture
def class_setup(institution, document_type):
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
            max_enrollment=1,
        )
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-1",
        )
        student = Student.objects.create(
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
    return {"school_class": school_class, "student": student}


def _enrollment_post_data(school_class, **overrides):
    document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
    data = {
        "school_class": school_class.pk,
        "presented_document_type": document_type.pk,
        "presented_document_number": "005LA00123",
        "document_issue_date": "2020-01-01",
        "document_issue_place": "Nacional - Luanda",
        "notes": "",
    }
    data.update(overrides)
    return data


def test_index_lists_the_two_flows(secretary_client):
    response = secretary_client.get("/inscricoes/")

    assert response.status_code == 200


def test_search_finds_student_by_number_document_or_name(secretary_client, class_setup):
    student = class_setup["student"]

    by_number = secretary_client.get("/inscricoes/matriculas/", {"q": str(student.student_number)})
    by_document = secretary_client.get("/inscricoes/matriculas/", {"q": "005LA00123"})
    by_name = secretary_client.get("/inscricoes/matriculas/", {"q": "Hangalo"})

    assert list(by_number.context["students"]) == [student]
    assert list(by_document.context["students"]) == [student]
    assert list(by_name.context["students"]) == [student]


def test_search_with_no_query_returns_no_students(secretary_client, class_setup):
    response = secretary_client.get("/inscricoes/matriculas/")

    assert list(response.context["students"]) == []


def test_enrollment_form_prefills_the_students_own_data(secretary_client, class_setup):
    student = class_setup["student"]

    response = secretary_client.get(f"/inscricoes/matriculas/{student.id}/nova/")

    assert response.status_code == 200
    assert response.context["student"] == student


def test_saving_creates_the_enrollment_with_derived_course_year_and_cycle(
    secretary_client, class_setup
):
    student = class_setup["student"]
    school_class = class_setup["school_class"]

    response = secretary_client.post(
        f"/inscricoes/matriculas/{student.id}/nova/",
        _enrollment_post_data(school_class),
    )

    assert response.status_code == 200
    enrollment = Enrollment.all_objects.get(student=student)
    assert enrollment.enrollment_number == 1
    assert enrollment.course == school_class.course
    assert enrollment.academic_year == school_class.academic_year
    assert enrollment.curricular_year == school_class.curricular_year
    assert enrollment.cycle == school_class.course.cycle
    assert enrollment.status == Enrollment.Status.PENDING


def test_enrollment_is_blocked_once_the_class_is_full(
    secretary_client, class_setup, institution, document_type
):
    school_class = class_setup["school_class"]
    student = class_setup["student"]

    # max_enrollment=1 in the fixture: enroll a second student first to fill it.
    with tenant_context(institution.id):
        guardian2 = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado 2",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="ENC-2",
        )
        other_student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2012, 1, 1),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="OTHER-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian2,
        )
    secretary_client.post(
        f"/inscricoes/matriculas/{other_student.id}/nova/",
        _enrollment_post_data(school_class, presented_document_number="OTHER-DOC"),
    )

    response = secretary_client.post(
        f"/inscricoes/matriculas/{student.id}/nova/", _enrollment_post_data(school_class)
    )

    assert response.status_code == 200
    assert "school_class" in response.context["form"].errors
    assert not Enrollment.all_objects.filter(student=student).exists()


def test_unauthenticated_user_cannot_search_or_enroll(client, class_setup):
    student = class_setup["student"]

    assert client.get("/inscricoes/matriculas/").status_code == 302
    assert client.get(f"/inscricoes/matriculas/{student.id}/nova/").status_code == 302
