"""Tests for the attendance grid views (issue #66, RF-FREQ-01)."""

from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile
from apps.attendance.models import Attendance
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

SELECTION_URL = reverse("attendance:attendance_grid_selection")
GRID_URL = reverse("attendance:attendance_grid")

MONDAY = date(2026, 3, 2)


@pytest.fixture
def teacher_client(teacher):
    client = Client()
    client.force_login(teacher)
    return client


def test_selection_forbidden_for_non_teacher_profile(institution, user_factory):
    guardian = user_factory(profile=Profile.GUARDIAN, institution=institution)
    client = Client()
    client.force_login(guardian)

    response = client.get(SELECTION_URL)

    assert response.status_code == 403


def test_selection_lists_the_teachers_own_schedule(teacher_client, schedule):
    response = teacher_client.get(SELECTION_URL)

    assert response.status_code == 200
    assert schedule.subject.name in response.content.decode()


def test_grid_lists_the_class_students(teacher_client, schedule, enrollment):
    response = teacher_client.get(GRID_URL, {"horario": str(schedule.id), "data": "2026-03-02"})

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_grid_is_forbidden_for_a_teacher_without_a_matching_schedule(
    institution, schedule, user_factory
):
    other_teacher = user_factory(
        username="professor2", profile=Profile.TEACHER, institution=institution
    )
    client = Client()
    client.force_login(other_teacher)

    response = client.post(
        GRID_URL,
        {
            "horario": str(schedule.id),
            "data": "2026-03-02",
        },
    )

    assert response.status_code == 403
    with tenant_context(institution.id):
        assert not Attendance.objects.exists()


def test_saving_the_grid_marks_attendance(
    teacher_client, institution, teacher, schedule, enrollment
):
    response = teacher_client.post(
        GRID_URL,
        {
            "horario": str(schedule.id),
            "data": "2026-03-02",
            f"falta_{enrollment.id}": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        attendance = Attendance.objects.get(enrollment=enrollment, schedule=schedule)
    assert attendance.status == Attendance.Status.ABSENT
    assert attendance.registered_by_id == teacher.id


def test_saving_the_grid_without_checking_falta_marks_present(
    teacher_client, institution, teacher, schedule, enrollment
):
    response = teacher_client.post(
        GRID_URL,
        {"horario": str(schedule.id), "data": "2026-03-02"},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        attendance = Attendance.objects.get(enrollment=enrollment, schedule=schedule)
    assert attendance.status == Attendance.Status.PRESENT


def test_saving_the_grid_with_falta_and_justificada_marks_justified(
    teacher_client, institution, teacher, schedule, enrollment
):
    response = teacher_client.post(
        GRID_URL,
        {
            "horario": str(schedule.id),
            "data": "2026-03-02",
            f"falta_{enrollment.id}": "on",
            f"justificada_{enrollment.id}": "on",
        },
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        attendance = Attendance.objects.get(enrollment=enrollment, schedule=schedule)
    assert attendance.status == Attendance.Status.JUSTIFIED_ABSENT
