"""Teste de integração ponta-a-ponta: Inscrição -> Matrícula (issue #155,
docs/13-testes-e-qualidade.md §13.1).

Reproduz o exemplo do documento original (aluna Yolene Hangalo,
docs/06-modulos-e-funcionalidades.md §6.4) através do `Client` do Django,
percorrendo os ecrãs reais na ordem em que uma Secretaria os usaria:
inscrição do aluno -> busca do aluno -> nova matrícula -- em vez de chamar
`apps.enrollment.services` directamente, como os testes unitários de cada
etapa já fazem."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Enrollment, Guardian, Student

pytestmark = pytest.mark.django_db

INSCRICAO_URL = reverse("enrollment:student_inscription")
BUSCA_URL = reverse("enrollment:student_search")


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
def school_class(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=uuid.uuid4(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=uuid.uuid4(), designation="1.º Ciclo", order=1
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        return SchoolClass.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )


def test_full_flow_from_inscricao_to_matricula(
    secretary_client, document_type, school_class, institution
):
    # 1. Inscrição: regista a aluna e o encarregado de educação (RF-MAT-02).
    inscricao_response = secretary_client.post(
        INSCRICAO_URL,
        {
            "student-first_name": "Yolene",
            "student-last_name": "Hangalo",
            "student-birth_date": "2012-04-10",
            "student-gender": "female",
            "student-document_type": document_type.pk,
            "student-document_number": "005LA00123",
            "student-document_issue_date": "2020-01-01",
            "student-document_issue_place": "Nacional - Luanda",
            "student-mobile_phone": "923000000",
            "guardian-full_name": "Encarregado Hangalo",
            "guardian-kinship": "mother",
            "guardian-document_type": document_type.pk,
            "guardian-document_number": "ENC-001",
            "guardian_consent_given": "on",
        },
    )

    assert inscricao_response.status_code == 200
    student = Student.all_objects.get(document_number="005LA00123")
    assert student.student_number == 1
    assert str(student) == "Yolene Hangalo (#1)"
    guardian = Guardian.all_objects.get(document_number="ENC-001")
    assert student.guardian_consent_given_by == guardian

    # 2. Busca do aluno (RF-MAT-04): a Secretaria já não sabe o `student_id`
    # de cor -- é assim que o encontra antes de matricular, tal como no
    # ecrã real (não passando o pk directamente na URL, como os testes
    # unitários de `enrollment_create_view` fazem).
    busca_response = secretary_client.get(BUSCA_URL, {"q": "005LA00123"})

    assert busca_response.status_code == 200
    found_students = list(busca_response.context["students"])
    assert found_students == [student]

    # 3. Matrícula (RF-MAT-05/06/07): "Guardar e Imprimir" grava a matrícula
    # e emite o comprovativo em PDF na mesma acção (issue #48).
    matricula_url = reverse("enrollment:enrollment_create", args=[student.id])
    matricula_response = secretary_client.post(
        matricula_url,
        {
            "school_class": str(school_class.id),
            "presented_document_type": document_type.pk,
            "presented_document_number": "005LA00123",
            "document_issue_date": "2020-01-01",
            "document_issue_place": "Nacional - Luanda",
            "notes": "",
        },
    )

    assert matricula_response.status_code == 200
    assert matricula_response["Content-Type"] == "application/pdf"
    assert matricula_response.content.startswith(b"%PDF-")

    enrollment = Enrollment.all_objects.get(student=student, school_class=school_class)
    assert enrollment.status in (Enrollment.Status.PENDING, Enrollment.Status.ACTIVE)
    with tenant_context(institution.id):
        assert school_class.active_enrollment_count() == 1
