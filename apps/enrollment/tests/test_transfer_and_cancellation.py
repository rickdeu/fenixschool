"""Tests for anulação (issue #51) and transferência (issue #49) de
matrícula, preservando o histórico do aluno."""

import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import SchoolClass
from apps.core.context import tenant_context
from apps.enrollment.models import Enrollment
from apps.enrollment.services import (
    MatriculaJaEncerradaError,
    MotivoAnulacaoObrigatorioError,
    SchoolClassFullError,
    anular_matricula,
    transferir_aluno,
)

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def other_school_class(institution, academic_year, course, curricular_year):
    with tenant_context(institution.id):
        return SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10B",
            designation="10.ª B",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.AFTERNOON,
        )


def test_anular_matricula_requires_a_reason(institution, enrollment, user_factory):
    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        with pytest.raises(MotivoAnulacaoObrigatorioError):
            anular_matricula(enrollment=enrollment, reason="   ", cancelled_by=officer)

        enrollment.refresh_from_db()
        assert enrollment.status != Enrollment.Status.CANCELLED


def test_anular_matricula_with_a_reason_cancels_it(institution, enrollment, user_factory):
    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        result = anular_matricula(
            enrollment=enrollment, reason="Desistência do aluno.", cancelled_by=officer
        )

    assert result.status == Enrollment.Status.CANCELLED
    assert result.cancellation_reason == "Desistência do aluno."


def test_anular_matricula_rejects_an_already_closed_enrollment(
    institution, enrollment, user_factory
):
    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        anular_matricula(enrollment=enrollment, reason="Primeira anulação.", cancelled_by=officer)

        with pytest.raises(MatriculaJaEncerradaError):
            anular_matricula(
                enrollment=enrollment, reason="Segunda tentativa.", cancelled_by=officer
            )


def test_enrollment_model_rejects_cancelled_status_without_a_reason(institution, enrollment):
    with tenant_context(institution.id):
        enrollment.status = Enrollment.Status.CANCELLED
        with pytest.raises(ValidationError):
            enrollment.save()


def test_transferir_aluno_preserves_history(
    institution, enrollment, other_school_class, user_factory
):
    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        new_enrollment = transferir_aluno(
            enrollment=enrollment,
            school_class=other_school_class,
            transferred_by=officer,
            origin_node_id=_origin(),
        )

        enrollment.refresh_from_db()

    assert enrollment.status == Enrollment.Status.TRANSFERRED
    assert new_enrollment.previous_enrollment_id == enrollment.id
    assert new_enrollment.school_class == other_school_class
    assert new_enrollment.student_id == enrollment.student_id
    assert new_enrollment.status == Enrollment.Status.PENDING


def test_transferir_aluno_respects_the_new_class_capacity(
    institution, enrollment, other_school_class, user_factory
):
    other_school_class.max_enrollment = 0
    with tenant_context(institution.id):
        other_school_class.save(update_fields=["max_enrollment"])

    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        with pytest.raises(SchoolClassFullError):
            transferir_aluno(
                enrollment=enrollment,
                school_class=other_school_class,
                transferred_by=officer,
                origin_node_id=_origin(),
            )

        enrollment.refresh_from_db()
        assert enrollment.status not in (Enrollment.Status.TRANSFERRED,)


def test_transferir_aluno_rejects_an_already_closed_enrollment(
    institution, enrollment, other_school_class, user_factory
):
    officer = user_factory(institution=institution)
    with tenant_context(institution.id):
        anular_matricula(enrollment=enrollment, reason="Anulada antes.", cancelled_by=officer)

        with pytest.raises(MatriculaJaEncerradaError):
            transferir_aluno(
                enrollment=enrollment,
                school_class=other_school_class,
                transferred_by=officer,
                origin_node_id=_origin(),
            )
