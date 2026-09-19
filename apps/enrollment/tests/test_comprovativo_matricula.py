"""Tests for the comprovativo de matrícula PDF (issue #48, RF-MAT-06):
generated automatically the moment the matrícula is saved, never a
separate opt-in step."""

import uuid

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.audit.models import AuditLogEntry
from apps.enrollment.services import emitir_comprovativo_matricula
from apps.reports.models import IssuedDocument

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


def test_emitir_comprovativo_matricula_returns_a_valid_pdf(institution, enrollment, user_factory):
    officer = user_factory(profile=Profile.SECRETARY, institution=institution)

    issued, pdf = emitir_comprovativo_matricula(
        enrollment=enrollment, issued_by=officer, origin_node_id=_origin()
    )

    assert issued.document_type == "comprovativo-matricula"
    assert issued.number == 1
    assert pdf.startswith(b"%PDF-")


def test_emitir_comprovativo_matricula_creates_an_audit_log_entry(
    institution, enrollment, user_factory
):
    officer = user_factory(profile=Profile.SECRETARY, institution=institution)

    issued, _pdf = emitir_comprovativo_matricula(
        enrollment=enrollment, issued_by=officer, origin_node_id=_origin()
    )

    entry = AuditLogEntry.objects.get(entity="reports.IssuedDocument", entity_id=str(issued.pk))
    assert entry.action == AuditLogEntry.Action.CREATE


def test_saving_an_enrollment_returns_the_comprovativo_pdf_directly(
    admin_client, institution, student, school_class, document_type
):
    url = reverse("enrollment:enrollment_create", args=[student.id])

    response = admin_client.post(
        url,
        {
            "school_class": str(school_class.id),
            "presented_document_type": document_type.code,
            "presented_document_number": student.document_number,
            "document_issue_date": "2020-01-01",
            "document_issue_place": "Nacional - Luanda",
            "notes": "",
            "is_repeating": "",
        },
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert IssuedDocument.all_objects.filter(
        institution=institution, document_type="comprovativo-matricula"
    ).exists()
