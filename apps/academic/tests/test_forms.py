"""Tests for `apps.academic.forms.ScheduleAdminForm` -- the only place a
schedule conflict (issue #37) is actually enforced today, since issue #36 is
model+admin only (a dedicated grid, issue #59, is separate, later M2 work).

Goes through the real Django Admin add view (not a bare `ScheduleAdminForm(...)`
instantiation): `ModelAdmin.get_form()` rebuilds `ModelChoiceField` querysets
fresh on every request, inside that request's own tenant context
(`TenantMiddleware`) -- instantiating the form class directly would instead
reuse whatever queryset got baked in at Python import time, with no tenant
context active at all, and every choice would wrongly look invalid.
"""

import uuid
from datetime import date

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

ADD_URL = reverse("admin:academic_schedule_add")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
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
    return {
        "institution": institution,
        "subject": subject,
        "school_class": school_class,
        "room": room,
        "teacher": teacher,
    }


def _form_data(setup, **overrides):
    data = {
        "institution": str(setup["institution"].pk),
        "school_class": str(setup["school_class"].pk),
        "subject": str(setup["subject"].pk),
        "weekday": Schedule.Weekday.MONDAY,
        "start_time": "08:00",
        "end_time": "09:30",
        "regime": Schedule.Regime.THEORETICAL,
        "room": str(setup["room"].pk),
        "teacher": str(setup["teacher"].pk),
        "origin_node_id": str(_origin()),
        "version": "1",
    }
    data.update(overrides)
    return data


def test_valid_data_is_accepted(admin_client, setup):
    response = admin_client.post(ADD_URL, _form_data(setup), follow=True)

    with tenant_context(setup["institution"].id):
        assert Schedule.objects.filter(school_class=setup["school_class"]).exists()
    assert response.status_code == 200


def test_a_teacher_conflict_is_rejected(admin_client, setup):
    with tenant_context(setup["institution"].id):
        Schedule.objects.create(
            institution=setup["institution"],
            origin_node_id=_origin(),
            school_class=setup["school_class"],
            subject=setup["subject"],
            weekday=Schedule.Weekday.MONDAY,
            start_time="08:00",
            end_time="09:30",
            regime=Schedule.Regime.THEORETICAL,
            room=setup["room"],
            teacher=setup["teacher"],
        )

    response = admin_client.post(
        ADD_URL,
        _form_data(setup, start_time="09:00", end_time="10:00"),
    )

    assert response.status_code == 200  # redisplays the form with an error
    assert "docente" in response.content.decode()
    with tenant_context(setup["institution"].id):
        assert Schedule.objects.filter(school_class=setup["school_class"]).count() == 1
