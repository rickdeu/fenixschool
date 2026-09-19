"""Tests for the dedicated "Turmas" screen (RF-CURR-05, issue #34) -- até
agora só existia como Django Admin; pedido directo do utilizador por um
ecrã real."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin_panel:school_class_list")
CREATE_URL = reverse("admin_panel:school_class_create")


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
def setup(institution):
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
    return {
        "course": course,
        "curricular_year": curricular_year,
        "academic_year": academic_year,
        "school_class": school_class,
    }


def test_requires_login(client):
    response = client.get(LIST_URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_secretary_can_view_but_not_create(secretary_client, setup):
    list_response = secretary_client.get(LIST_URL)
    create_response = secretary_client.get(CREATE_URL)

    assert list_response.status_code == 200
    assert create_response.status_code == 403


def test_lists_every_school_class_grouped_by_academic_year(admin_client, setup):
    response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    groups = response.context["groups"]
    assert len(groups) == 1
    assert groups[0]["academic_year"] == setup["academic_year"]
    assert groups[0]["school_classes"] == [setup["school_class"]]


def test_filters_by_academic_year(admin_client, institution, setup):
    with tenant_context(institution.id):
        other_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2027/2028",
            start_date=date(2027, 2, 1),
            end_date=date(2027, 12, 15),
        )

    response = admin_client.get(LIST_URL, {"ano_lectivo": str(other_year.id)})

    assert response.status_code == 200
    groups = response.context["groups"]
    assert len(groups) == 1
    assert groups[0]["academic_year"] == other_year
    assert groups[0]["school_classes"] == []


def test_creates_a_school_class(admin_client, setup):
    response = admin_client.post(
        CREATE_URL,
        {
            "code": "10B",
            "designation": "10.ª B",
            "academic_year": str(setup["academic_year"].id),
            "course": str(setup["course"].id),
            "curricular_year": str(setup["curricular_year"].id),
            "shift": SchoolClass.Shift.AFTERNOON,
            "max_enrollment": 36,
        },
        follow=True,
    )

    assert response.status_code == 200
    assert SchoolClass.all_objects.filter(code="10B").exists()


def test_edits_a_school_class(admin_client, setup):
    url = reverse("admin_panel:school_class_edit", args=[setup["school_class"].id])

    response = admin_client.post(
        url,
        {
            "code": "10A",
            "designation": "10.ª A (renomeada)",
            "academic_year": str(setup["academic_year"].id),
            "course": str(setup["course"].id),
            "curricular_year": str(setup["curricular_year"].id),
            "shift": SchoolClass.Shift.MORNING,
            "max_enrollment": 40,
        },
        follow=True,
    )

    assert response.status_code == 200
    setup["school_class"].refresh_from_db()
    assert setup["school_class"].designation == "10.ª A (renomeada)"
    assert setup["school_class"].max_enrollment == 40


def test_deletes_an_unused_school_class(admin_client, setup):
    url = reverse("admin_panel:school_class_edit", args=[setup["school_class"].id])

    response = admin_client.post(url, {"delete": "1"}, follow=True)

    assert response.status_code == 200
    assert not SchoolClass.all_objects.filter(pk=setup["school_class"].id).exists()


def test_cannot_delete_a_school_class_with_enrollments(admin_client, institution, setup):
    from apps.core.models import IdentificationDocumentType
    from apps.enrollment.models import Guardian, Student
    from apps.enrollment.services import enroll_student

    with tenant_context(institution.id):
        document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
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
        enroll_student(
            institution=institution,
            student=student,
            school_class=setup["school_class"],
            origin_node_id=_origin(),
            course=setup["course"],
            academic_year=setup["academic_year"],
            cycle=setup["curricular_year"].course.cycle,
            curricular_year=setup["curricular_year"],
            presented_document_type=document_type,
            presented_document_number="005LA00123",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )

    url = reverse("admin_panel:school_class_edit", args=[setup["school_class"].id])
    response = admin_client.post(url, {"delete": "1"}, follow=True)

    assert response.status_code == 200
    assert SchoolClass.all_objects.filter(pk=setup["school_class"].id).exists()


def _enroll(institution, setup, *, first_name, last_name):
    from apps.core.models import IdentificationDocumentType
    from apps.enrollment.models import Guardian, Student
    from apps.enrollment.services import enroll_student

    with tenant_context(institution.id):
        document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number=f"ENC-{first_name}",
        )
        student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name=first_name,
            last_name=last_name,
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number=f"005LA{first_name}",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )
        return enroll_student(
            institution=institution,
            student=student,
            school_class=setup["school_class"],
            origin_node_id=_origin(),
            course=setup["course"],
            academic_year=setup["academic_year"],
            cycle=setup["curricular_year"].course.cycle,
            curricular_year=setup["curricular_year"],
            presented_document_type=document_type,
            presented_document_number=f"005LA{first_name}",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )


def test_school_class_students_view_lists_enrolled_students(admin_client, institution, setup):
    _enroll(institution, setup, first_name="Yolene", last_name="Hangalo")

    url = reverse("admin_panel:school_class_students", args=[setup["school_class"].id])
    response = admin_client.get(url)

    assert response.status_code == 200
    assert b"Yolene" in response.content


def test_school_class_students_view_shows_empty_state(admin_client, setup):
    url = reverse("admin_panel:school_class_students", args=[setup["school_class"].id])
    response = admin_client.get(url)

    assert response.status_code == 200
    assert "Nenhum aluno matriculado nesta turma." in response.content.decode()
