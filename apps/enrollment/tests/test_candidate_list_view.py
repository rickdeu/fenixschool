"""Tests for the candidate list/admission entry point (issue #42, RF-MAT-10)."""

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
from apps.enrollment.models import Candidate

pytestmark = pytest.mark.django_db

URL = "/inscricoes/candidatos/"


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


def _make_candidate(institution, course, document_type, *, full_name, status):
    with tenant_context(institution.id):
        return Candidate.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name=full_name,
            birth_date=date(2012, 4, 10),
            document_type=document_type,
            document_number=f"DOC-{full_name}",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
            status=status,
        )


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


def test_shows_only_pending_candidates(secretary_client, institution, course, document_type):
    pending = _make_candidate(
        institution, course, document_type, full_name="Pendente", status=Candidate.Status.PENDING
    )
    _make_candidate(
        institution, course, document_type, full_name="Admitido", status=Candidate.Status.ADMITTED
    )
    _make_candidate(
        institution, course, document_type, full_name="Rejeitado", status=Candidate.Status.REJECTED
    )

    response = secretary_client.get(URL)

    assert response.status_code == 200
    candidates = list(response.context["candidates"])
    assert candidates == [pending]


def test_admit_link_points_to_the_inscription_form_with_the_candidate_id(
    secretary_client, institution, course, document_type
):
    candidate = _make_candidate(
        institution, course, document_type, full_name="Pendente", status=Candidate.Status.PENDING
    )

    response = secretary_client.get(URL)

    expected_url = f"{reverse('enrollment:student_inscription')}?candidate={candidate.id}"
    assert expected_url in response.content.decode()
