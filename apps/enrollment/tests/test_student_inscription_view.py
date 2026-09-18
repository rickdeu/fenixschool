"""Tests for the Inscrição view (issue #45, RF-MAT-02, docs/06-modulos-e-
funcionalidades.md §6.4)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, Department
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, IdentificationDocumentType
from apps.enrollment.models import Candidate, Guardian, Student, StudentGuardian

pytestmark = pytest.mark.django_db

URL = "/inscricoes/alunos/novo/"


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


def _valid_post_data(document_type, **overrides):
    data = {
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
    }
    data.update(overrides)
    return data


def test_unauthenticated_user_is_redirected_to_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_user_without_permission_is_forbidden(institution):
    User.objects.create_user(
        username="aluno1", institution=institution, profile=Profile.STUDENT, password="x"
    )
    client = Client()
    client.login(username="aluno1", password="x")

    response = client.get(URL)

    assert response.status_code == 403


def test_secretary_can_view_the_form(secretary_client):
    response = secretary_client.get(URL)

    assert response.status_code == 200
    assert "student_form" in response.context
    assert "guardian_form" in response.context


def test_registering_with_a_new_guardian_creates_everything_atomically(
    secretary_client, document_type
):
    response = secretary_client.post(URL, _valid_post_data(document_type))

    assert response.status_code == 200
    student = Student.all_objects.get(document_number="005LA00123")
    guardian = Guardian.all_objects.get(document_number="ENC-001")
    assert student.student_number == 1
    assert student.guardian_consent_given_by == guardian
    link = StudentGuardian.all_objects.get(student=student, guardian=guardian)
    assert link.is_primary
    assert link.financially_responsible


def test_searching_finds_an_existing_guardian_by_document(
    secretary_client, institution, document_type
):
    with tenant_context(institution.id):
        existing = Guardian.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name="Encarregado Existente",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="ENC-EXISTING",
        )

    response = secretary_client.get(URL, {"document_number": "ENC-EXISTING"})

    assert response.status_code == 200
    assert response.context["found_guardian"] == existing
    assert response.context["guardian_not_found"] is False


def test_searching_an_unknown_document_reports_not_found(secretary_client):
    response = secretary_client.get(URL, {"document_number": "DOES-NOT-EXIST"})

    assert response.context["found_guardian"] is None
    assert response.context["guardian_not_found"] is True


def test_registering_with_an_existing_guardian_reuses_it_without_creating_a_new_one(
    secretary_client, institution, document_type
):
    with tenant_context(institution.id):
        existing = Guardian.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name="Encarregado Existente",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="ENC-EXISTING",
        )

    data = _valid_post_data(document_type)
    data.pop("guardian-full_name")
    data.pop("guardian-kinship")
    data.pop("guardian-document_type")
    data.pop("guardian-document_number")
    data["existing_guardian_id"] = str(existing.pk)

    secretary_client.post(URL, data)

    assert Guardian.all_objects.count() == 1
    student = Student.all_objects.get(document_number="005LA00123")
    assert student.guardian_consent_given_by == existing


def test_registration_is_blocked_without_consent(secretary_client, document_type):
    data = _valid_post_data(document_type)
    del data["guardian_consent_given"]

    response = secretary_client.post(URL, data)

    assert response.status_code == 200
    assert "guardian_consent_given" in response.context["consent_form"].errors
    assert not Student.all_objects.exists()
    assert not Guardian.all_objects.exists()


def test_duplicate_student_document_is_rejected_with_a_clear_message(
    secretary_client, document_type
):
    secretary_client.post(URL, _valid_post_data(document_type))

    response = secretary_client.post(
        URL, _valid_post_data(document_type, **{"guardian-document_number": "ENC-002"})
    )

    assert response.status_code == 200
    assert "document_number" in response.context["student_form"].errors
    assert Student.all_objects.count() == 1


def test_invalid_student_data_does_not_create_a_guardian_either(secretary_client, document_type):
    data = _valid_post_data(document_type)
    del data["student-first_name"]

    secretary_client.post(URL, data)

    assert not Student.all_objects.exists()
    assert not Guardian.all_objects.exists()


@pytest.fixture
def course(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=uuid.uuid4(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=uuid.uuid4(), designation="1.º Ciclo", order=1
        )
        return Course.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )


@pytest.fixture
def pending_candidate(institution, course, document_type):
    with tenant_context(institution.id):
        return Candidate.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name="Yolene Hangalo",
            birth_date=date(2012, 4, 10),
            document_type=document_type,
            document_number="005LA00123",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
        )


def test_admitting_a_candidate_prefills_the_student_form(secretary_client, pending_candidate):
    response = secretary_client.get(URL, {"candidate": str(pending_candidate.pk)})

    assert response.status_code == 200
    assert response.context["candidate"] == pending_candidate
    assert response.context["student_form"].initial["first_name"] == "Yolene"
    assert response.context["student_form"].initial["last_name"] == "Hangalo"
    assert response.context["student_form"].initial["document_number"] == "005LA00123"


def test_admitting_a_candidate_marks_it_admitted_once_the_student_is_created(
    secretary_client, pending_candidate, document_type, institution
):
    data = _valid_post_data(document_type)
    data["candidate_id"] = str(pending_candidate.pk)

    response = secretary_client.post(URL, data)

    assert response.status_code == 200
    with tenant_context(institution.id):
        pending_candidate.refresh_from_db()
    assert pending_candidate.status == Candidate.Status.ADMITTED


def test_a_candidate_is_not_marked_admitted_if_registration_fails(
    secretary_client, pending_candidate, document_type, institution
):
    data = _valid_post_data(document_type)
    data["candidate_id"] = str(pending_candidate.pk)
    del data["guardian_consent_given"]

    response = secretary_client.post(URL, data)

    assert response.status_code == 200
    with tenant_context(institution.id):
        pending_candidate.refresh_from_db()
    assert pending_candidate.status == Candidate.Status.PENDING


def test_an_already_admitted_candidate_cannot_be_admitted_again(
    secretary_client, pending_candidate, institution
):
    with tenant_context(institution.id):
        pending_candidate.status = Candidate.Status.ADMITTED
        pending_candidate.save(update_fields=["status"])

    response = secretary_client.get(URL, {"candidate": str(pending_candidate.pk)})

    assert response.status_code == 200
    assert response.context["candidate"] is None
    assert response.context["student_form"].initial == {}
