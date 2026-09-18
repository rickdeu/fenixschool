"""Tests for the per-profile "Tarefas Actuais" dashboard (issue #119) shown
at the post-login landing page (issue #24)."""

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
from apps.enrollment.models import Candidate, Guardian, Student

pytestmark = pytest.mark.django_db

URL = reverse("accounts:landing_placeholder")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def course(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
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
def teacher_client(institution):
    User.objects.create_user(
        username="professor1",
        institution=institution,
        profile=Profile.TEACHER,
        password="senha-forte-123",
    )
    client = Client()
    client.login(username="professor1", password="senha-forte-123")
    return client


def test_teacher_sees_the_honest_placeholder_not_fabricated_widgets(teacher_client):
    response = teacher_client.get(URL)

    assert response.status_code == 200
    assert response.context["widgets"] == []
    assert "ainda está por construir" in response.content.decode()


def test_secretary_sees_pending_candidates_widget(
    secretary_client, institution, course, document_type
):
    with tenant_context(institution.id):
        Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="DOC-1",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
            status=Candidate.Status.PENDING,
        )

    response = secretary_client.get(URL)

    widgets = {w["title"]: w for w in response.context["widgets"]}
    assert widgets["Candidaturas por processar"]["count"] == 1
    assert widgets["Candidaturas por processar"]["url"] == reverse("enrollment:candidate_list")


def test_secretary_sees_admitted_not_yet_enrolled_widget(
    secretary_client, institution, course, document_type
):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Yolene Hangalo",
            birth_date=date(2012, 4, 10),
            document_type=document_type,
            document_number="DOC-2",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
            status=Candidate.Status.ADMITTED,
        )
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-1",
        )
        Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Yolene",
            last_name="Hangalo",
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="DOC-2",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
            admitted_from_candidate=candidate,
        )

    response = secretary_client.get(URL)

    widgets = {w["title"]: w for w in response.context["widgets"]}
    assert widgets["Alunos admitidos por matricular"]["count"] == 1
    assert widgets["Alunos admitidos por matricular"]["url"] == reverse(
        "enrollment:bulk_enrollment"
    )


def test_guardian_is_redirected_to_their_own_portal(institution):
    User.objects.create_user(
        username="encarregado1",
        institution=institution,
        profile=Profile.GUARDIAN,
        password="senha-forte-123",
    )
    client = Client()
    client.login(username="encarregado1", password="senha-forte-123")

    response = client.get(URL)

    assert response.status_code == 302
    assert response.url == reverse("guardian_portal:dashboard")
