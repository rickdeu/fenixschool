"""Tests for the Boletim screens and PDF export (issue #97, RF-REL-04):
selecção de aluno/trimestre, extracto de notas por disciplina e exportação
oficial em PDF."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.audit.models import AuditLogEntry
from apps.core.context import tenant_context
from apps.grading.models import Grade
from apps.grading.services import registar_media_final, set_institution_default_formula
from apps.reports.models import IssuedDocument

pytestmark = pytest.mark.django_db

SELECTION_URL = reverse("grading:boletim_selection")
BOLETIM_URL = reverse("grading:boletim")
PDF_URL = reverse("grading:boletim_pdf")


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
def final_grade(institution, enrollment, subject, evaluation_type, academic_term, teacher):
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
        return registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )


def test_selection_forbidden_for_non_privileged_profile(institution, user_factory):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.get(SELECTION_URL)

    assert response.status_code == 403


def test_selection_lists_enrolled_students(admin_client, enrollment, school_class, academic_term):
    response = admin_client.get(
        SELECTION_URL, {"turma": str(school_class.id), "periodo": str(academic_term.id)}
    )

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_boletim_shows_final_grades(admin_client, final_grade, enrollment, academic_term):
    response = admin_client.get(
        BOLETIM_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)}
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert final_grade.subject.name in content
    # Formatação de decimais localizada em pt (vírgula, não ponto) --
    # ver `django.utils.formats.number_format`.
    assert "15,00" in content


def test_pdf_export_is_forbidden_for_non_privileged_profile(
    institution, user_factory, final_grade, enrollment, academic_term
):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.post(
        PDF_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)}
    )

    assert response.status_code == 403


def test_pdf_export_returns_a_valid_pdf(
    admin_client, institution, final_grade, enrollment, academic_term
):
    response = admin_client.post(
        PDF_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

    issued = IssuedDocument.all_objects.get(institution=institution)
    assert issued.document_type == "boletim"
    assert issued.number == 1


def test_pdf_export_creates_an_audit_log_entry(
    admin_client, institution, final_grade, enrollment, academic_term
):
    admin_client.post(PDF_URL, {"aluno": str(enrollment.id), "periodo": str(academic_term.id)})

    issued = IssuedDocument.all_objects.get(institution=institution)
    entry = AuditLogEntry.objects.get(entity="reports.IssuedDocument", entity_id=str(issued.pk))
    assert entry.action == AuditLogEntry.Action.CREATE
