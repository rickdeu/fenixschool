"""Tests for the candidate list/admission entry point (issue #42, RF-MAT-10)."""

import uuid
from datetime import date
from decimal import Decimal

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


def test_also_shows_second_call_candidates(secretary_client, institution, course, document_type):
    second_call = _make_candidate(
        institution,
        course,
        document_type,
        full_name="Segunda Chamada",
        status=Candidate.Status.SECOND_CALL,
    )

    response = secretary_client.get(URL)

    assert second_call in response.context["candidates"]


def test_filters_by_course(secretary_client, institution, course, document_type):
    other_course = Course.objects.create(
        institution=institution,
        origin_node_id=uuid.uuid4(),
        code="OUT",
        name="Outro Curso",
        created_on=date(2020, 1, 1),
        department=course.department,
        cycle=course.cycle,
        duration_years=4,
    )
    matching = _make_candidate(
        institution, course, document_type, full_name="Certo", status=Candidate.Status.PENDING
    )
    _make_candidate(
        institution,
        other_course,
        document_type,
        full_name="Outro",
        status=Candidate.Status.PENDING,
    )

    response = secretary_client.get(URL, {"curso": str(course.id)})

    assert list(response.context["candidates"]) == [matching]


def test_filters_by_name_or_document(secretary_client, institution, course, document_type):
    matching = _make_candidate(
        institution,
        course,
        document_type,
        full_name="Yolene Hangalo",
        status=Candidate.Status.PENDING,
    )
    _make_candidate(
        institution, course, document_type, full_name="Outro Aluno", status=Candidate.Status.PENDING
    )

    response = secretary_client.get(URL, {"q": "Yolene"})

    assert list(response.context["candidates"]) == [matching]


def test_registering_a_score_via_htmx_updates_the_candidates_state(
    secretary_client, institution, course, document_type
):
    candidate = _make_candidate(
        institution, course, document_type, full_name="Pendente", status=Candidate.Status.PENDING
    )

    response = secretary_client.post(
        reverse("enrollment:candidate_score_save"),
        {"candidate_id": str(candidate.id), "score": "8"},
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        candidate.refresh_from_db()
    assert candidate.exam_score == 8
    content = response.content.decode()
    assert "Não apto" in content
    # Reportado ao vivo: com uma nota fraccionária a formatação por omissão
    # em pt (vírgula) tornava o value="..." do <input type="number">
    # inválido para o browser, que mostrava o campo vazio -- parecia que a
    # nota "desaparecia" ao recarregar a página, apesar de já gravada.
    with tenant_context(institution.id):
        candidate.exam_score = Decimal("8.5")
        candidate.save(update_fields=["exam_score"])
    response2 = secretary_client.get(reverse("enrollment:candidate_list"))
    content2 = response2.content.decode()
    assert 'value="8.5"' in content2
    assert 'value="8,5"' not in content2


def test_convoking_a_failing_candidate_for_a_second_call(
    secretary_client, institution, course, document_type
):
    candidate = _make_candidate(
        institution, course, document_type, full_name="Pendente", status=Candidate.Status.PENDING
    )
    with tenant_context(institution.id):
        candidate.exam_score = 5
        candidate.save(update_fields=["exam_score"])

    response = secretary_client.post(
        URL, {"candidate_id": str(candidate.id), "action": "segunda_chamada"}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        candidate.refresh_from_db()
    assert candidate.status == Candidate.Status.SECOND_CALL


def test_bulk_admit_action_accepts_selected_eligible_candidates(
    secretary_client, institution, course, document_type
):
    first = _make_candidate(
        institution, course, document_type, full_name="Primeiro", status=Candidate.Status.PENDING
    )
    second = _make_candidate(
        institution, course, document_type, full_name="Segundo", status=Candidate.Status.PENDING
    )

    response = secretary_client.post(
        URL,
        {"action": "admitir_lote", "candidate_ids": [str(first.id), str(second.id)]},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        first.refresh_from_db()
        second.refresh_from_db()
    assert first.status == Candidate.Status.ACCEPTED
    assert second.status == Candidate.Status.ACCEPTED


def test_accepted_candidate_can_still_be_admitted_into_inscription(
    secretary_client, institution, course, document_type
):
    candidate = _make_candidate(
        institution, course, document_type, full_name="Aceite", status=Candidate.Status.ACCEPTED
    )

    response = secretary_client.get(
        reverse("enrollment:student_inscription"), {"candidate": str(candidate.id)}
    )

    assert response.status_code == 200
    assert response.context["candidate"] == candidate


def test_ineligible_candidate_cannot_be_admitted(
    secretary_client, institution, course, document_type
):
    candidate = _make_candidate(
        institution, course, document_type, full_name="Reprovado", status=Candidate.Status.PENDING
    )
    with tenant_context(institution.id):
        candidate.exam_score = 5
        candidate.save(update_fields=["exam_score"])

    response = secretary_client.get(
        reverse("enrollment:student_inscription"), {"candidate": str(candidate.id)}
    )

    assert response.status_code == 200
    assert response.context["candidate"] is None
    assert response.context["candidate_ineligible"] is True
