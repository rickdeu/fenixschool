"""Tests for the data export screen (issue #117, RF-ADM-05)."""

import csv
import io
import json
import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, SchoolClass, Subject
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Guardian, Student
from apps.enrollment.services import enroll_student
from apps.grading.models import EvaluationType, Grade

pytestmark = pytest.mark.django_db

URL = reverse("admin_panel:data_export")


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
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def grade(institution, document_type):
    with tenant_context(institution.id):
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
        enrollment = enroll_student(
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
        academic_term = academic_year.terms.create(
            institution=institution,
            origin_node_id=_origin(),
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )
        evaluation_type = EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight=Decimal("0.3"),
        )
        teacher = User.objects.create_user(
            username="professor1", institution=institution, profile=Profile.TEACHER
        )
        return Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("15"),
            teacher=teacher,
        )


def test_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_the_institution_admin_permission(institution, user_factory):
    secretary = user_factory(profile=Profile.SECRETARY, institution=institution)
    client = Client()
    client.force_login(secretary)

    response = client.get(URL)

    assert response.status_code == 403


def test_lists_every_exportable_entity(admin_client):
    response = admin_client.get(URL)

    assert response.status_code == 200
    labels = {e["label"] for e in response.context["entities"]}
    assert labels == {"Alunos", "Matrículas", "Notas"}


def test_unknown_entity_404s(admin_client):
    response = admin_client.get(URL, {"entidade": "financeiro", "formato": "csv"})

    assert response.status_code == 404


def test_unknown_format_404s(admin_client, grade):
    response = admin_client.get(URL, {"entidade": "alunos", "formato": "xml"})

    assert response.status_code == 404


def test_csv_export_of_students(admin_client, grade):
    response = admin_client.get(URL, {"entidade": "alunos", "formato": "csv"})

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    rows = list(csv.reader(io.StringIO(response.content.decode())))
    assert rows[0] == [
        "Nº de aluno",
        "Nome",
        "Data de nascimento",
        "Género",
        "Nº de documento",
        "Estado",
    ]
    assert "Yolene Hangalo" in rows[1][1]


def test_json_export_of_grades(admin_client, grade):
    response = admin_client.get(URL, {"entidade": "notas", "formato": "json"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    data = json.loads(response.content)
    assert float(data[0]["value"]) == 15.0


def test_pdf_export_of_enrollments(admin_client, grade):
    response = admin_client.get(URL, {"entidade": "matriculas", "formato": "pdf"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_export_is_scoped_to_the_admins_own_institution(admin_client, grade):
    from apps.core.factories import InstitutionFactory

    other_institution = InstitutionFactory()
    with tenant_context(other_institution.id):
        Student.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.MALE,
            document_type=IdentificationDocumentType.objects.get(code="bilhete-de-identidade"),
            document_number="OTHER-001",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=Guardian.objects.create(
                institution=other_institution,
                origin_node_id=_origin(),
                full_name="Outro Encarregado",
                kinship=Guardian.Kinship.FATHER,
                document_type=IdentificationDocumentType.objects.get(code="bilhete-de-identidade"),
                document_number="OTHER-ENC-001",
            ),
        )

    response = admin_client.get(URL, {"entidade": "alunos", "formato": "csv"})

    content = response.content.decode()
    assert "Outro Aluno" not in content
    assert "Yolene Hangalo" in content
