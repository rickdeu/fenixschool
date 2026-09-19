"""Tests for the student history/detail screen (issues #49/#50/#51):
anular, transferir, and the enrollment history itself."""

import uuid

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.enrollment.models import Enrollment

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


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


def _url(student):
    return reverse("enrollment:student_detail", args=[student.id])


def test_forbidden_for_a_teacher(institution, student, user_factory):
    teacher = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher)

    response = client.get(_url(student))

    assert response.status_code == 403


def test_shows_the_enrollment_history(secretary_client, student, enrollment):
    response = secretary_client.get(_url(student))

    assert response.status_code == 200
    content = response.content.decode()
    assert str(enrollment.academic_year) in content


def test_cancelling_without_a_reason_shows_an_error(secretary_client, institution, enrollment):
    response = secretary_client.post(
        _url(enrollment.student), {"action": "anular", "reason": "   "}, follow=True
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        enrollment.refresh_from_db()
    assert enrollment.status != Enrollment.Status.CANCELLED
    assert "motivo" in response.content.decode().lower()


def test_cancelling_with_a_reason_cancels_the_enrollment(secretary_client, institution, enrollment):
    response = secretary_client.post(
        _url(enrollment.student),
        {"action": "anular", "reason": "Desistência do aluno."},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.CANCELLED
    assert enrollment.cancellation_reason == "Desistência do aluno."


def test_transferring_creates_a_new_enrollment_and_marks_the_old_one(
    secretary_client, institution, enrollment, other_school_class
):
    response = secretary_client.post(
        _url(enrollment.student),
        {"action": "transferir", "school_class": str(other_school_class.id)},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.TRANSFERRED
        new_enrollment = Enrollment.objects.get(previous_enrollment=enrollment)
    assert new_enrollment.school_class == other_school_class
