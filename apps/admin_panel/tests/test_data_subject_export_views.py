"""Tests for the data subject export screen (issue #144, RF-.../9.1, Lei
n.º 22/11)."""

import json
import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian, Student, StudentGuardian

pytestmark = pytest.mark.django_db

SEARCH_URL = reverse("admin_panel:data_subject_export")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


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
def guardian(institution, document_type):
    with tenant_context(institution.id):
        return Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado Hangalo",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-001",
            mobile_phone="923000000",
        )


@pytest.fixture
def student(institution, document_type, guardian):
    with tenant_context(institution.id):
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
        StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=guardian,
            is_primary=True,
            financially_responsible=True,
        )
        return student


def test_requires_login(client):
    response = client.get(SEARCH_URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_the_institution_admin_permission(institution, user_factory):
    secretary = user_factory(profile=Profile.SECRETARY, institution=institution)
    client = Client()
    client.force_login(secretary)

    response = client.get(SEARCH_URL)

    assert response.status_code == 403


def test_search_finds_the_student_by_document_number(admin_client, student):
    response = admin_client.get(SEARCH_URL, {"q": "005LA00123"})

    assert response.status_code == 200
    assert list(response.context["students"]) == [student]


def test_search_finds_the_guardian_by_exact_document_number(admin_client, guardian):
    """`Guardian.document_number` está cifrado (issue #141) -- só suporta
    correspondência exacta, não `icontains`."""
    response = admin_client.get(SEARCH_URL, {"q": "ENC-001"})

    assert response.status_code == 200
    assert list(response.context["guardians"]) == [guardian]


def test_search_finds_the_guardian_by_name(admin_client, guardian):
    response = admin_client.get(SEARCH_URL, {"q": "Hangalo"})

    assert response.status_code == 200
    assert list(response.context["guardians"]) == [guardian]


def test_student_export_includes_every_section(admin_client, student, guardian):
    url = reverse("admin_panel:data_subject_export_student", args=[student.id])

    response = admin_client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Yolene" in content
    assert "Encarregado Hangalo" in content  # guardian's real name, decrypted.


def test_student_export_json_download_contains_the_students_own_data(
    admin_client, student, guardian
):
    url = reverse("admin_panel:data_subject_export_student", args=[student.id])

    response = admin_client.get(url, {"formato": "json"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert "attachment" in response["Content-Disposition"]
    data = json.loads(response.content)
    assert data["aluno"]["first_name"] == "Yolene"
    assert data["encarregados_de_educacao"][0]["full_name"] == "Encarregado Hangalo"
    assert data["encarregados_de_educacao"][0]["document_number"] == "ENC-001"


def test_guardian_export_lists_associated_students_without_their_full_profile(
    admin_client, student, guardian
):
    url = reverse("admin_panel:data_subject_export_guardian", args=[guardian.id])

    response = admin_client.get(url, {"formato": "json"})

    data = json.loads(response.content)
    assert data["encarregado_de_educacao"]["full_name"] == "Encarregado Hangalo"
    assert data["alunos_associados"] == [
        {
            "aluno_id": str(student.id),
            "numero_de_aluno": student.student_number,
            "nome": str(student),
            "is_primary": True,
            "financially_responsible": True,
        }
    ]


def test_export_is_scoped_to_the_admins_own_institution(admin_client, document_type):
    from apps.core.factories import InstitutionFactory

    other_institution = InstitutionFactory()
    with tenant_context(other_institution.id):
        other_guardian = Guardian.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            full_name="Outro Encarregado",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="OTHER-ENC-001",
        )
        other_student = Student.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="OTHER-001",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=other_guardian,
        )

    url = reverse("admin_panel:data_subject_export_student", args=[other_student.id])
    response = admin_client.get(url)

    assert response.status_code == 404
