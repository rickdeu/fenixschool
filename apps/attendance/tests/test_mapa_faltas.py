"""Tests for "Mapa de faltas por turma, docente e encarregado de
educação" (issue #69, RF-FREQ-04): each role sees the map with the right
scope."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.attendance.models import Attendance
from apps.attendance.services import mapa_faltas_aluno, mapa_faltas_turma
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)

MAP_URL = reverse("attendance:attendance_map")
DOCENTE_MAP_URL = reverse("attendance:docente_attendance_map")


def _origin():
    return uuid.uuid4()


def _mark(institution, enrollment, student, schedule, teacher, weeks, status):
    with tenant_context(institution.id):
        for week in range(weeks):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY + timedelta(days=7 * week),
                status=status,
                registered_by=teacher,
            )


@pytest.fixture
def secretary_client(institution, verify_two_factor):
    secretary = User.objects.create_user(
        username="secretaria1",
        institution=institution,
        profile=Profile.SECRETARY,
        password="senha-forte-123",
    )
    secretary.groups.add(Group.objects.get(name="Secretaria Escolar"))
    client = Client()
    client.login(username="secretaria1", password="senha-forte-123")
    verify_two_factor(client, secretary)
    return client


@pytest.fixture
def teacher_client(teacher):
    client = Client()
    client.force_login(teacher)
    return client


def test_mapa_faltas_aluno_summarizes_across_subjects(
    institution, enrollment, student, schedule, teacher
):
    _mark(
        institution,
        enrollment,
        student,
        schedule,
        teacher,
        weeks=13,
        status=Attendance.Status.ABSENT,
    )

    with tenant_context(institution.id):
        summary = mapa_faltas_aluno(enrollment=enrollment)

    assert summary["unjustified_absence_hours"] == Decimal("13")
    assert schedule.subject in summary["at_risk_subjects"]


def test_mapa_faltas_turma_lists_every_enrolled_student(institution, enrollment, school_class):
    with tenant_context(institution.id):
        rows = mapa_faltas_turma(institution=institution, school_class=school_class)

    assert len(rows) == 1
    assert rows[0]["enrollment"] == enrollment


def test_attendance_map_forbidden_for_a_teacher(institution, teacher):
    client = Client()
    client.force_login(teacher)

    response = client.get(MAP_URL)

    assert response.status_code == 403


def test_attendance_map_lists_students_for_the_selected_class(
    secretary_client, enrollment, school_class
):
    response = secretary_client.get(MAP_URL, {"turma": str(school_class.id)})

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_docente_map_forbidden_for_a_non_teacher_profile(institution, user_factory):
    guardian = user_factory(profile=Profile.GUARDIAN, institution=institution)
    client = Client()
    client.force_login(guardian)

    response = client.get(DOCENTE_MAP_URL)

    assert response.status_code == 403


def test_docente_map_lists_the_teachers_own_students(teacher_client, schedule, enrollment):
    response = teacher_client.get(DOCENTE_MAP_URL, {"horario": str(schedule.id)})

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_docente_map_forbidden_for_a_schedule_not_their_own(
    institution, schedule, enrollment, user_factory
):
    other_teacher = user_factory(
        username="professor2", profile=Profile.TEACHER, institution=institution
    )
    client = Client()
    client.force_login(other_teacher)

    response = client.get(DOCENTE_MAP_URL, {"horario": str(schedule.id)})

    assert response.status_code == 403
