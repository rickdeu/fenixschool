"""Tests for the "Pauta" detail screen (issue #60, RF-AVAL-04): viewing,
editing (before homologar) and homologando/reabrindo a pauta of one turma/
disciplina/tipo/trimestre combination."""

import uuid
from decimal import Decimal
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import Grade
from apps.grading.services import homologar_pauta

pytestmark = pytest.mark.django_db

URL = reverse("grading:pauta_detail")
SAVE_URL = reverse("grading:pauta_grade_cell_save")


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


def _url(school_class, subject, evaluation_type, academic_term):
    query = _query(school_class, subject, evaluation_type, academic_term)
    return f"{URL}?{urlencode(query)}"


def test_non_privileged_profile_is_forbidden(
    institution, user_factory, school_class, subject, evaluation_type, academic_term
):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.get(URL, _query(school_class, subject, evaluation_type, academic_term))

    assert response.status_code == 403


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
        _url(school_class, subject, evaluation_type, academic_term),
        {"grade_ids": [str(grade.pk)], "action": "homologar"},
        follow=True,
    )

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is True


def test_reabrir_without_a_reason_is_rejected(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    with tenant_context(institution.id):
        homologar_pauta(Grade.objects.filter(pk=grade.pk), user=grade.teacher)

    response = admin_client.post(
        _url(school_class, subject, evaluation_type, academic_term),
        {"grade_ids": [str(grade.pk)], "action": "reabrir", "reason": "   "},
        follow=True,
    )

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.is_grade_report_closed is True


def test_reabrir_with_a_reason_reopens(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    with tenant_context(institution.id):
        homologar_pauta(Grade.objects.filter(pk=grade.pk), user=grade.teacher)

    response = admin_client.post(
        _url(school_class, subject, evaluation_type, academic_term),
        {
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


def test_non_privileged_profile_cannot_edit_a_grade(institution, user_factory, grade):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.post(SAVE_URL, {"grade_id": str(grade.pk), "value": "18"})

    assert response.status_code == 403


def test_admin_can_correct_a_grade_before_sealing(admin_client, institution, grade):
    response = admin_client.post(SAVE_URL, {"grade_id": str(grade.pk), "value": "18"})

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.value == Decimal("18.0")
    assert "is-valid" in response.content.decode()


def test_cannot_edit_a_grade_after_homologar(admin_client, institution, grade):
    with tenant_context(institution.id):
        homologar_pauta(Grade.objects.filter(pk=grade.pk), user=grade.teacher)

    response = admin_client.post(SAVE_URL, {"grade_id": str(grade.pk), "value": "18"})

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.value == Decimal("15")
    assert "fechada" in response.content.decode().lower()


def test_rejects_a_value_outside_the_scale(admin_client, grade):
    response = admin_client.post(SAVE_URL, {"grade_id": str(grade.pk), "value": "25"})

    assert response.status_code == 200
    grade.refresh_from_db()
    assert grade.value == Decimal("15")
    assert "is-invalid" in response.content.decode()
