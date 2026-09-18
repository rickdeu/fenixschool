"""Tests for the "Pautas" screen (issue #60, RF-AVAL-04) -- the real
admin_panel-style replacement for the old Django Admin homologar/reabrir
actions (Django Admin is never used by real users)."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import Grade

pytestmark = pytest.mark.django_db

URL = reverse("grading:pauta_management")


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
def grade(institution, enrollment, subject, evaluation_type, academic_term, teacher):
    with tenant_context(institution.id):
        return Grade.objects.create(
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


def _query(school_class, subject, evaluation_type, academic_term):
    return {
        "turma": str(school_class.id),
        "disciplina": str(subject.id),
        "tipo": str(evaluation_type.id),
        "periodo": str(academic_term.id),
    }


def test_non_privileged_profile_is_forbidden(institution, user_factory):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.get(URL)

    assert response.status_code == 403


def test_selection_form_renders_without_a_query(admin_client):
    response = admin_client.get(URL)

    assert response.status_code == 200
    assert "rows" not in response.context or response.context["rows"] is None


def test_lists_the_pautas_grades(
    admin_client, grade, school_class, subject, evaluation_type, academic_term
):
    response = admin_client.get(URL, _query(school_class, subject, evaluation_type, academic_term))

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_homologar_closes_the_grades(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    response = admin_client.post(
        URL,
        {
            **_query(school_class, subject, evaluation_type, academic_term),
            "grade_ids": [str(grade.pk)],
            "action": "homologar",
        },
        follow=True,
    )

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is True


def test_reabrir_without_a_reason_is_rejected(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    with tenant_context(institution.id):
        from apps.grading.services import homologar_pauta

        homologar_pauta(Grade.objects.filter(pk=grade.pk), user=grade.teacher)

    response = admin_client.post(
        URL,
        {
            **_query(school_class, subject, evaluation_type, academic_term),
            "grade_ids": [str(grade.pk)],
            "action": "reabrir",
            "reason": "   ",
        },
        follow=True,
    )

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is True


def test_reabrir_with_a_reason_reopens(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    with tenant_context(institution.id):
        from apps.grading.services import homologar_pauta

        homologar_pauta(Grade.objects.filter(pk=grade.pk), user=grade.teacher)

    response = admin_client.post(
        URL,
        {
            **_query(school_class, subject, evaluation_type, academic_term),
            "grade_ids": [str(grade.pk)],
            "action": "reabrir",
            "reason": "Erro identificado após homologação.",
        },
        follow=True,
    )

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is False
    assert grade.reopening_reason == "Erro identificado após homologação."
