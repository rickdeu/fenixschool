"""Tests for RF-FREQ-03's "impacto sinalizado na situação final" (issue
#68): exceeding the legal absence limit for a disciplina marks it as
"em atraso" in `calcular_situacao_final`, even when its grades alone
would have passed (or when it was never graded at all)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.attendance.models import Attendance
from apps.core.context import tenant_context
from apps.grading.models import FinalSituation, Grade
from apps.grading.services import (
    calcular_situacao_final,
    registar_media_final,
    set_institution_default_formula,
)

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)


def _origin():
    return uuid.uuid4()


def _mark_absent(institution, enrollment, student, schedule, teacher, weeks):
    with tenant_context(institution.id):
        for week in range(weeks):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY + timedelta(days=7 * week),
                status=Attendance.Status.ABSENT,
                registered_by=teacher,
            )


def test_exceeding_the_absence_limit_fails_the_subject_despite_a_passing_grade(
    institution, enrollment, student, schedule, evaluation_type, academic_term, teacher
):
    subject = schedule.subject
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("18"),
            teacher=teacher,
        )
        registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )

    # weekly_hours=4 (grading conftest's `subject` fixture) -> limit=12h;
    # schedule is 1h/aula -> 13 unjustified absences exceeds it.
    _mark_absent(institution, enrollment, student, schedule, teacher, weeks=13)

    situation = calcular_situacao_final(enrollment)

    with tenant_context(institution.id):
        assert subject in situation.failed_subjects.all()
    assert situation.status != FinalSituation.Status.APPROVED


def test_exceeding_the_absence_limit_fails_an_ungraded_subject_too(
    institution, enrollment, student, schedule, teacher
):
    """A disciplina never graded yet is normally skipped -- but a student
    already past the legal absence limit for it is still at risk, grades
    or not."""
    subject = schedule.subject

    _mark_absent(institution, enrollment, student, schedule, teacher, weeks=13)

    situation = calcular_situacao_final(enrollment)

    with tenant_context(institution.id):
        assert subject in situation.failed_subjects.all()


def test_staying_under_the_absence_limit_does_not_fail_the_subject(
    institution, enrollment, student, schedule, evaluation_type, academic_term, teacher
):
    subject = schedule.subject
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("15"),
            teacher=teacher,
        )
        registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )

    _mark_absent(institution, enrollment, student, schedule, teacher, weeks=2)

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.APPROVED
    with tenant_context(institution.id):
        assert list(situation.failed_subjects.all()) == []


def test_justified_absences_never_trigger_the_limit(
    institution, enrollment, student, schedule, evaluation_type, academic_term, teacher
):
    subject = schedule.subject
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("15"),
            teacher=teacher,
        )
        registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )

        for week in range(20):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY + timedelta(days=7 * week),
                status=Attendance.Status.JUSTIFIED_ABSENT,
                registered_by=teacher,
            )

    situation = calcular_situacao_final(enrollment)

    assert situation.status == FinalSituation.Status.APPROVED
