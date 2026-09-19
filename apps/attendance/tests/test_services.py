"""Tests for `apps.attendance.services` (issue #66, RF-FREQ-01)."""

import uuid
from datetime import date

import pytest

from apps.accounts.models import Profile
from apps.attendance.models import Attendance
from apps.attendance.services import (
    DocenteNaoAssociadoError,
    get_docente_schedule_slots,
    registar_presencas,
)
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)


def _origin():
    return uuid.uuid4()


def test_get_docente_schedule_slots_only_lists_the_teachers_own(
    institution, teacher, schedule, user_factory
):
    other_teacher = user_factory(
        username="professor2", profile=Profile.TEACHER, institution=institution
    )

    with tenant_context(institution.id):
        assert list(get_docente_schedule_slots(teacher)) == [schedule]
        assert list(get_docente_schedule_slots(other_teacher)) == []


def test_get_docente_schedule_slots_shows_everything_to_a_super_admin(
    institution, schedule, user_factory
):
    admin = user_factory(
        profile=Profile.SUPER_ADMIN, institution=institution, is_superuser=True
    )

    with tenant_context(institution.id):
        assert schedule in list(get_docente_schedule_slots(admin))


def test_registar_presencas_creates_records(institution, teacher, schedule, enrollment):
    with tenant_context(institution.id):
        results = registar_presencas(
            teacher=teacher,
            schedule=schedule,
            date=MONDAY,
            statuses={str(enrollment.id): Attendance.Status.PRESENT},
            origin_node_id=_origin(),
        )

    assert len(results) == 1
    assert results[0].status == Attendance.Status.PRESENT


def test_registar_presencas_updates_an_existing_record_instead_of_duplicating(
    institution, teacher, schedule, enrollment
):
    with tenant_context(institution.id):
        registar_presencas(
            teacher=teacher,
            schedule=schedule,
            date=MONDAY,
            statuses={str(enrollment.id): Attendance.Status.PRESENT},
            origin_node_id=_origin(),
        )
        registar_presencas(
            teacher=teacher,
            schedule=schedule,
            date=MONDAY,
            statuses={str(enrollment.id): Attendance.Status.ABSENT},
            origin_node_id=_origin(),
        )

        assert Attendance.objects.filter(enrollment=enrollment, schedule=schedule).count() == 1
        assert (
            Attendance.objects.get(enrollment=enrollment, schedule=schedule).status
            == Attendance.Status.ABSENT
        )


def test_registar_presencas_rejects_a_teacher_not_associated_with_the_schedule(
    institution, schedule, enrollment, user_factory
):
    other_teacher = user_factory(
        username="professor2", profile=Profile.TEACHER, institution=institution
    )

    with tenant_context(institution.id):
        with pytest.raises(DocenteNaoAssociadoError):
            registar_presencas(
                teacher=other_teacher,
                schedule=schedule,
                date=MONDAY,
                statuses={str(enrollment.id): Attendance.Status.PRESENT},
                origin_node_id=_origin(),
            )


def test_registar_presencas_allows_a_super_admin_regardless_of_schedule(
    institution, schedule, enrollment, user_factory
):
    admin = user_factory(
        profile=Profile.SUPER_ADMIN, institution=institution, is_superuser=True
    )

    with tenant_context(institution.id):
        results = registar_presencas(
            teacher=admin,
            schedule=schedule,
            date=MONDAY,
            statuses={str(enrollment.id): Attendance.Status.JUSTIFIED_ABSENT},
            origin_node_id=_origin(),
        )

    assert results[0].status == Attendance.Status.JUSTIFIED_ABSENT
