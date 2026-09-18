"""Tests for the room/teacher occupancy map (issue #38, RF-CURR-06)."""

import uuid
from datetime import date, time

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import (
    Course,
    CurricularYear,
    Department,
    Room,
    Schedule,
    SchoolClass,
    Subject,
)
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear

pytestmark = pytest.mark.django_db

URL = reverse("admin_panel:schedule_occupancy")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def pedagogical_client(institution, verify_two_factor):
    user = User.objects.create_user(
        username="direcao1",
        institution=institution,
        profile=Profile.PEDAGOGICAL_DIRECTION,
        password="senha-forte-123",
    )
    user.groups.add(Group.objects.get(name="Direção Pedagógica"))
    client = Client()
    client.login(username="direcao1", password="senha-forte-123")
    verify_two_factor(client, user)
    return client


@pytest.fixture
def setup(institution):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT",
            name="Matemática",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        school_class = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )
        room = Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=30
        )
        teacher = User.objects.create_user(
            username="professor1", institution=institution, profile=Profile.TEACHER, password="x"
        )
        schedule = Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=teacher,
        )
    return {
        "room": room,
        "teacher": teacher,
        "school_class": school_class,
        "schedule": schedule,
    }


def test_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_permission(institution):
    User.objects.create_user(
        username="aluno1", institution=institution, profile=Profile.STUDENT, password="x"
    )
    client = Client()
    client.login(username="aluno1", password="x")

    response = client.get(URL)

    assert response.status_code == 403


def test_pedagogical_direction_can_see_the_map(pedagogical_client, setup):
    response = pedagogical_client.get(URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Matemática" in content
    assert "10.ª A" in content
    assert "Sala 1" in content


def test_filter_by_room_excludes_other_rooms(pedagogical_client, institution, setup):
    with tenant_context(institution.id):
        other_room = Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 2", capacity=20
        )

    response = pedagogical_client.get(URL, {"room": str(other_room.pk)})

    assert response.status_code == 200
    assert "Matemática" not in response.content.decode()


def test_filter_by_teacher(pedagogical_client, institution, setup):
    response = pedagogical_client.get(URL, {"teacher": str(setup["teacher"].pk)})

    assert response.status_code == 200
    assert "Matemática" in response.content.decode()


def test_filter_by_school_class(pedagogical_client, institution, setup):
    response = pedagogical_client.get(URL, {"school_class": str(setup["school_class"].pk)})

    assert response.status_code == 200
    assert "Matemática" in response.content.decode()
