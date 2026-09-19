"""Tests for `Candidate` (issue #42, docs/05-modelo-de-dados.md §5.14, RF-MAT-10)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.academic.models import Course, Department
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, IdentificationDocumentType
from apps.enrollment.models import Candidate
from apps.enrollment.services import (
    CandidateAlreadyDecidedError,
    CandidateAlreadyEligibleError,
    ExamScoreOutOfRangeError,
    aceitar_candidatos_em_lote,
    convocar_para_segunda_chamada,
    registar_nota_candidato,
)

pytestmark = pytest.mark.django_db


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
def candidate(institution, course, document_type):
    with tenant_context(institution.id):
        return Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="004928474HA038",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
        )


def test_candidate_defaults_to_pending(institution, course, document_type):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="004928474HA038",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
        )

    assert candidate.status == Candidate.Status.PENDING
    assert str(candidate) == "Pedro Neto"


def test_candidate_without_a_score_is_eligible_by_default(candidate):
    assert candidate.exam_score is None
    assert candidate.is_eligible_for_admission is True


def test_registering_a_passing_score_keeps_the_candidate_eligible(institution, candidate):
    with tenant_context(institution.id):
        registar_nota_candidato(candidate=candidate, score=Decimal("12"))

    assert candidate.exam_score == Decimal("12.0")
    assert candidate.is_eligible_for_admission is True
    assert candidate.status == Candidate.Status.PENDING


def test_registering_a_failing_score_makes_the_candidate_ineligible(institution, candidate):
    with tenant_context(institution.id):
        registar_nota_candidato(candidate=candidate, score=Decimal("8"))

    assert candidate.is_eligible_for_admission is False


def test_registering_a_score_uses_the_institutions_configured_passing_score(institution, candidate):
    institution.admission_exam_passing_score = Decimal("14")
    institution.save()

    with tenant_context(institution.id):
        registar_nota_candidato(candidate=candidate, score=Decimal("12"))

    assert candidate.is_eligible_for_admission is False


def test_score_out_of_the_0_20_scale_is_rejected(institution, candidate):
    with tenant_context(institution.id):
        with pytest.raises(ExamScoreOutOfRangeError):
            registar_nota_candidato(candidate=candidate, score=Decimal("21"))
        with pytest.raises(ExamScoreOutOfRangeError):
            registar_nota_candidato(candidate=candidate, score=Decimal("-1"))


def test_cannot_register_a_score_for_an_already_decided_candidate(institution, candidate):
    candidate.status = Candidate.Status.ADMITTED
    candidate.save(update_fields=["status"])

    with tenant_context(institution.id):
        with pytest.raises(CandidateAlreadyDecidedError):
            registar_nota_candidato(candidate=candidate, score=Decimal("15"))


def test_convocar_para_segunda_chamada_requires_a_failing_score(institution, candidate):
    with tenant_context(institution.id):
        with pytest.raises(CandidateAlreadyEligibleError):
            convocar_para_segunda_chamada(candidate=candidate)

        registar_nota_candidato(candidate=candidate, score=Decimal("5"))
        convocar_para_segunda_chamada(candidate=candidate)

    assert candidate.status == Candidate.Status.SECOND_CALL


def test_a_second_call_retake_re_evaluates_eligibility(institution, candidate):
    with tenant_context(institution.id):
        registar_nota_candidato(candidate=candidate, score=Decimal("5"))
        convocar_para_segunda_chamada(candidate=candidate)

        registar_nota_candidato(candidate=candidate, score=Decimal("15"))

    assert candidate.status == Candidate.Status.PENDING
    assert candidate.is_eligible_for_admission is True


def test_cannot_convoke_an_already_decided_candidate(institution, candidate):
    candidate.status = Candidate.Status.REJECTED
    candidate.save(update_fields=["status"])

    with tenant_context(institution.id):
        with pytest.raises(CandidateAlreadyDecidedError):
            convocar_para_segunda_chamada(candidate=candidate)


def test_bulk_accepting_only_accepts_eligible_candidates(institution, course, document_type):
    with tenant_context(institution.id):
        eligible = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Apto",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="DOC-APTO",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
        )
        failing = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Reprovado",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="DOC-REPROVADO",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
            exam_score=Decimal("5"),
        )

        count = aceitar_candidatos_em_lote(
            institution=institution, candidate_ids=[eligible.id, failing.id]
        )

        eligible.refresh_from_db()
        failing.refresh_from_db()

    assert count == 1
    assert eligible.status == Candidate.Status.ACCEPTED
    assert failing.status == Candidate.Status.PENDING


def test_student_defaults_prefills_name_birth_date_and_document(institution, course, document_type):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Pedro Neto",
            birth_date=date(2011, 3, 15),
            document_type=document_type,
            document_number="004928474HA038",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
        )

    defaults = candidate.student_defaults()

    assert defaults == {
        "first_name": "Pedro",
        "last_name": "Neto",
        "birth_date": date(2011, 3, 15),
        "document_type": document_type.code,
        "document_number": "004928474HA038",
    }
