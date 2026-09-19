"""Tests for `SchoolClassAdmin`'s legal-ceiling warning (issue #174,
RF-CURR-05): "aviso, não bloqueio automático" quando `max_enrollment`
ultrapassa o tecto legal (Decreto Presidencial 162/23)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear

pytestmark = pytest.mark.django_db


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
def class_setup(institution):
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
    return {
        "course": course,
        "curricular_year": curricular_year,
        "academic_year": academic_year,
        "school_class": school_class,
    }


def _change_url(school_class):
    return reverse("admin:academic_schoolclass_change", args=[school_class.pk])


def _post_data(institution, class_setup, max_enrollment):
    school_class = class_setup["school_class"]
    return {
        "institution": str(institution.id),
        "origin_node_id": str(school_class.origin_node_id),
        "code": school_class.code,
        "designation": school_class.designation,
        "academic_year": str(class_setup["academic_year"].id),
        "course": str(class_setup["course"].id),
        "curricular_year": str(class_setup["curricular_year"].id),
        "shift": SchoolClass.Shift.MORNING,
        "max_enrollment": max_enrollment,
        "version": school_class.version,
    }


def test_saving_within_the_legal_ceiling_warns_of_nothing(
    admin_client, institution, class_setup
):
    response = admin_client.post(
        _change_url(class_setup["school_class"]),
        _post_data(institution, class_setup, max_enrollment=36),
        follow=True,
    )

    assert response.status_code == 200
    assert "ultrapassa o tecto legal" not in response.content.decode()


def test_saving_above_the_legal_ceiling_warns_but_still_saves(
    admin_client, institution, class_setup
):
    response = admin_client.post(
        _change_url(class_setup["school_class"]),
        _post_data(institution, class_setup, max_enrollment=50),
        follow=True,
    )

    assert response.status_code == 200
    assert "ultrapassa o tecto legal" in response.content.decode()

    class_setup["school_class"].refresh_from_db()
    assert class_setup["school_class"].max_enrollment == 50
