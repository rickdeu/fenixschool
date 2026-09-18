"""Tests for the FinalSituation model and calcular_situacao_final() service
(issue #62, RF-AVAL-07)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import Subject
from apps.core.context import tenant_context
from apps.core.factories import InstitutionFactory
from apps.grading.models import FinalSituation, Grade
from apps.grading.services import (
    calcular_situacao_final,
    registar_media_final,
    set_institution_default_formula,
)

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def _grade_and_final(
    institution, enrollment, subject, evaluation_type, academic_term, teacher, value
):
    with tenant_context(institution.id):
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal(value),
            teacher=teacher,
        )
        return registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )


@pytest.fixture(autouse=True)
def _single_component_formula(institution, evaluation_type):
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})


def test_approved_when_every_graded_subject_passes(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    _grade_and_final(
        institution, enrollment, subject, evaluation_type, academic_term, teacher, "15"
    )

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.APPROVED
    assert list(situation.failed_subjects.all()) == []


def test_ungraded_subjects_are_skipped_not_counted_as_failed(
    institution, enrollment, course, curricular_year
):
    """A disciplina without any `FinalGrade` yet hasn't been evaluated --
    `calcular_situacao_final` doesn't fabricate a failing result for it."""
    with tenant_context(institution.id):
        Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="UNGRADED",
            name="Disciplina Sem Notas",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=course.cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=2,
        )

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.APPROVED


def test_pending_recovery_when_failed_subjects_are_within_the_recoverable_limit(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    assert institution.max_recoverable_subjects == 2
    _grade_and_final(institution, enrollment, subject, evaluation_type, academic_term, teacher, "8")

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.PENDING_RECOVERY
    with tenant_context(institution.id):
        assert list(situation.failed_subjects.all()) == [subject]


def test_failed_when_failed_subjects_exceed_the_recoverable_limit(
    institution, enrollment, course, curricular_year, academic_term, evaluation_type, teacher
):
    institution.max_recoverable_subjects = 1
    institution.save(update_fields=["max_recoverable_subjects"])

    with tenant_context(institution.id):
        subject_a = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="A",
            name="Disciplina A",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=course.cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=2,
        )
        subject_b = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="B",
            name="Disciplina B",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=course.cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=2,
        )

    _grade_and_final(
        institution, enrollment, subject_a, evaluation_type, academic_term, teacher, "5"
    )
    _grade_and_final(
        institution, enrollment, subject_b, evaluation_type, academic_term, teacher, "6"
    )

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.FAILED
    with tenant_context(institution.id):
        assert set(situation.failed_subjects.all()) == {subject_a, subject_b}


def test_a_manual_override_on_the_final_grade_is_taken_into_account(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    from apps.grading.services import ajustar_media_manualmente

    final_grade = _grade_and_final(
        institution, enrollment, subject, evaluation_type, academic_term, teacher, "5"
    )
    with tenant_context(institution.id):
        ajustar_media_manualmente(
            final_grade=final_grade,
            user=teacher,
            value=Decimal("15"),
            reason="Avaliação de recurso.",
        )

        situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.APPROVED


def test_is_idempotent_and_recalculable(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    """Re-running after a Nota changes (ex.: issue #61's recurso) updates
    the same row instead of creating a second one, and reflects the new
    result."""
    final_grade = _grade_and_final(
        institution, enrollment, subject, evaluation_type, academic_term, teacher, "8"
    )
    first = calcular_situacao_final(enrollment)
    assert first.status == FinalSituation.Status.PENDING_RECOVERY

    with tenant_context(institution.id):
        grade = Grade.objects.get(enrollment=enrollment, subject=subject)
        grade.value = Decimal("15")
        grade.save()
        registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )

    second = calcular_situacao_final(enrollment)

    assert second.pk == first.pk
    assert second.status == FinalSituation.Status.APPROVED
    assert list(second.failed_subjects.all()) == []
    with tenant_context(institution.id):
        assert FinalSituation.objects.filter(enrollment=enrollment).count() == 1
    assert final_grade  # keeps the fixture referenced/used


def test_clean_requires_the_same_institution(institution, enrollment):
    other_institution = InstitutionFactory()
    situation = FinalSituation(
        institution=other_institution,
        origin_node_id=_origin(),
        enrollment=enrollment,
        status=FinalSituation.Status.APPROVED,
    )

    with pytest.raises(ValidationError):
        situation.save()


def test_str(institution, enrollment, subject, evaluation_type, academic_term, teacher):
    _grade_and_final(
        institution, enrollment, subject, evaluation_type, academic_term, teacher, "15"
    )

    situation = calcular_situacao_final(enrollment)

    assert "Yolene Hangalo" in str(situation)
    assert "Aprovado" in str(situation)


# -- lancar_nota_recurso() (issue #61, RF-AVAL-06) --------------------------


def test_lancar_nota_recurso_resolves_a_failed_subject(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    from apps.grading.services import lancar_nota_recurso

    _grade_and_final(institution, enrollment, subject, evaluation_type, academic_term, teacher, "6")
    situation = calcular_situacao_final(enrollment)
    assert situation.status == FinalSituation.Status.PENDING_RECOVERY

    with tenant_context(institution.id):
        grade = lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("12"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )

    assert grade.evaluation_type.name == "Exame de Recurso"
    situation.refresh_from_db()
    assert situation.status == FinalSituation.Status.APPROVED
    with tenant_context(institution.id):
        assert list(situation.failed_subjects.all()) == []


def test_lancar_nota_recurso_rejects_a_subject_that_is_not_failed(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    from apps.grading.services import DisciplinaNaoEstaEmRecursoError, lancar_nota_recurso

    _grade_and_final(
        institution, enrollment, subject, evaluation_type, academic_term, teacher, "15"
    )
    calcular_situacao_final(enrollment)

    with tenant_context(institution.id), pytest.raises(DisciplinaNaoEstaEmRecursoError):
        lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("18"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )


def test_lancar_nota_recurso_rejects_a_subject_with_no_final_situation_yet(
    institution, enrollment, subject, teacher, academic_term
):
    from apps.grading.services import DisciplinaNaoEstaEmRecursoError, lancar_nota_recurso

    with tenant_context(institution.id), pytest.raises(DisciplinaNaoEstaEmRecursoError):
        lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("18"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )


def test_lancar_nota_recurso_below_the_passing_grade_does_not_resolve_it(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    from apps.grading.services import lancar_nota_recurso

    _grade_and_final(institution, enrollment, subject, evaluation_type, academic_term, teacher, "6")
    situation = calcular_situacao_final(enrollment)

    with tenant_context(institution.id):
        lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("8"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )

    situation.refresh_from_db()
    assert situation.status == FinalSituation.Status.PENDING_RECOVERY
    with tenant_context(institution.id):
        assert list(situation.failed_subjects.all()) == [subject]


def test_lancar_nota_recurso_is_idempotent_updates_the_same_grade(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    from apps.grading.services import lancar_nota_recurso

    _grade_and_final(institution, enrollment, subject, evaluation_type, academic_term, teacher, "6")
    calcular_situacao_final(enrollment)

    with tenant_context(institution.id):
        first = lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("8"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )
        second = lancar_nota_recurso(
            enrollment=enrollment,
            subject=subject,
            value=Decimal("15"),
            teacher=teacher,
            academic_term=academic_term,
            origin_node_id=uuid.uuid4(),
        )

        assert (
            Grade.objects.filter(
                enrollment=enrollment, subject=subject, evaluation_type__name="Exame de Recurso"
            ).count()
            == 1
        )

    assert first.pk == second.pk
    assert second.value == Decimal("15.0")
