"""Tests for `calcular_assiduidade` (issue #68, RF-FREQ-03)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.attendance.models import Attendance
from apps.attendance.services import calcular_assiduidade
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)


def _origin():
    return uuid.uuid4()


def _mark(institution, enrollment, student, schedule, teacher, day, status):
    with tenant_context(institution.id):
        return Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=day,
            status=status,
            registered_by=teacher,
        )


def test_no_records_yet_is_100_percent_with_no_risk(institution, enrollment, subject):
    with tenant_context(institution.id):
        result = calcular_assiduidade(enrollment=enrollment, subject=subject)

    assert result["attendance_percentage"] == Decimal("100.0")
    assert result["exceeds_limit"] is False


def test_calculates_the_attendance_percentage(
    institution, enrollment, student, schedule, teacher
):
    # `schedule` runs Mondays 08:00-09:00 (1 hour) -- 3 present, 1 absent.
    _mark(institution, enrollment, student, schedule, teacher, MONDAY, Attendance.Status.PRESENT)
    _mark(
        institution,
        enrollment,
        student,
        schedule,
        teacher,
        MONDAY + timedelta(days=7),
        Attendance.Status.PRESENT,
    )
    _mark(
        institution,
        enrollment,
        student,
        schedule,
        teacher,
        MONDAY + timedelta(days=14),
        Attendance.Status.PRESENT,
    )
    _mark(
        institution,
        enrollment,
        student,
        schedule,
        teacher,
        MONDAY + timedelta(days=21),
        Attendance.Status.ABSENT,
    )

    with tenant_context(institution.id):
        result = calcular_assiduidade(
            enrollment=enrollment, subject=schedule.subject
        )

    assert result["total_hours"] == Decimal("4")
    assert result["attendance_percentage"] == Decimal("75.0")


def test_justified_absences_count_for_percentage_but_not_the_legal_limit(
    institution, enrollment, student, schedule, teacher
):
    # weekly_hours=4 (conftest's `subject` fixture) -> limit = 3*4 = 12h.
    for week in range(20):
        _mark(
            institution,
            enrollment,
            student,
            schedule,
            teacher,
            MONDAY + timedelta(days=7 * week),
            Attendance.Status.JUSTIFIED_ABSENT,
        )

    with tenant_context(institution.id):
        result = calcular_assiduidade(enrollment=enrollment, subject=schedule.subject)

    # 20 hours of absence lower the percentage a lot, but none of it is
    # unjustified, so the legal limit is never triggered.
    assert result["attendance_percentage"] == Decimal("0.0")
    assert result["unjustified_absence_hours"] == Decimal("0")
    assert result["exceeds_limit"] is False


def test_exceeds_limit_once_unjustified_hours_pass_3x_weekly_load(
    institution, enrollment, student, schedule, teacher
):
    # weekly_hours=4 -> limit = 12h; schedule is 1h/aula -> 13 unjustified
    # absences (13h) exceeds it.
    for week in range(13):
        _mark(
            institution,
            enrollment,
            student,
            schedule,
            teacher,
            MONDAY + timedelta(days=7 * week),
            Attendance.Status.ABSENT,
        )

    with tenant_context(institution.id):
        result = calcular_assiduidade(enrollment=enrollment, subject=schedule.subject)

    assert result["unjustified_absence_hours"] == Decimal("13")
    assert result["limit_hours"] == Decimal("12")
    assert result["exceeds_limit"] is True


def test_academic_term_scopes_the_calculation(
    institution, enrollment, student, schedule, teacher, academic_term
):
    inside = academic_term.start_date + timedelta(days=1)  # 2026-02-02, a Monday
    outside = academic_term.end_date + timedelta(days=1)  # 2026-06-01, also a Monday

    _mark(institution, enrollment, student, schedule, teacher, inside, Attendance.Status.ABSENT)
    _mark(institution, enrollment, student, schedule, teacher, outside, Attendance.Status.ABSENT)

    with tenant_context(institution.id):
        result = calcular_assiduidade(
            enrollment=enrollment, subject=schedule.subject, academic_term=academic_term
        )

    assert result["total_hours"] == Decimal("1")
