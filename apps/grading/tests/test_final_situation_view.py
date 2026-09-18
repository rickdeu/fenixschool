"""Tests for the "Situação final" screen (issue #62, RF-AVAL-07) -- the
real admin_panel-style replacement for the old Django Admin
"Calcular situação final" action (Django Admin is never used by real
users)."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import FinalSituation, Grade
from apps.grading.services import registar_media_final, set_institution_default_formula

pytestmark = pytest.mark.django_db

URL = reverse("grading:final_situation")


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


def test_non_privileged_profile_is_forbidden(institution, user_factory):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.get(URL)

    assert response.status_code == 403


def test_lists_school_classes_as_occurrences(admin_client, enrollment, school_class):
    response = admin_client.get(URL)

    assert response.status_code == 200
    assert "rows" not in response.context or response.context["rows"] is None
    content = response.content.decode()
    assert school_class.designation in content


def test_lists_enrollments_for_the_selected_school_class(admin_client, enrollment, school_class):
    response = admin_client.get(URL, {"turma": str(school_class.id)})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Yolene Hangalo" in content
    assert "Ainda não calculada" in content
    assert 'id="select-all-enrollments"' in content


def test_calculating_shows_the_resulting_situation(
    admin_client,
    institution,
    enrollment,
    school_class,
    subject,
    evaluation_type,
    academic_term,
    teacher,
):
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

    response = admin_client.post(
        f"{URL}?turma={school_class.id}",
        {"enrollment_ids": [str(enrollment.pk)]},
        follow=True,
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        situation = FinalSituation.objects.get(enrollment=enrollment)
    assert situation.status == FinalSituation.Status.APPROVED
    assert "Aprovado" in response.content.decode()
