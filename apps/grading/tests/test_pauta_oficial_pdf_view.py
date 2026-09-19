"""Tests for the Pauta Oficial PDF export (issue #96, RF-REL-03): reuses
the same turma/disciplina/tipo/trimestre selection as `pauta_detail_view`,
delegating numbering/audit/rendering to `apps.reports.services`."""

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
from apps.reports.models import IssuedDocument

pytestmark = pytest.mark.django_db

URL = reverse("grading:pauta_oficial_pdf")


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


def _payload(school_class, subject, evaluation_type, academic_term):
    return {
        "turma": str(school_class.id),
        "disciplina": str(subject.id),
        "tipo": str(evaluation_type.id),
        "periodo": str(academic_term.id),
    }


def test_get_is_not_allowed(admin_client, school_class, subject, evaluation_type, academic_term):
    response = admin_client.get(
        URL, _payload(school_class, subject, evaluation_type, academic_term)
    )

    assert response.status_code == 405


def test_non_privileged_profile_is_forbidden(
    institution, user_factory, school_class, subject, evaluation_type, academic_term
):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.post(
        URL, _payload(school_class, subject, evaluation_type, academic_term)
    )

    assert response.status_code == 403


def test_exports_a_valid_pdf_with_the_official_numbering(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    response = admin_client.post(
        URL, _payload(school_class, subject, evaluation_type, academic_term)
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

    issued = IssuedDocument.all_objects.get(institution=institution)
    assert issued.document_type == "pauta-oficial"
    assert issued.number == 1
    assert f'filename="{issued.formatted_number.replace("/", "-")}.pdf"' in (
        response["Content-Disposition"]
    )


def test_export_creates_an_audit_log_entry(
    admin_client, institution, grade, school_class, subject, evaluation_type, academic_term
):
    admin_client.post(URL, _payload(school_class, subject, evaluation_type, academic_term))

    issued = IssuedDocument.all_objects.get(institution=institution)
    entry = AuditLogEntry.objects.get(entity="reports.IssuedDocument", entity_id=str(issued.pk))
    assert entry.action == AuditLogEntry.Action.CREATE
