"""Tests for Declarações (issue #94, RF-REL-01): selecção de turma,
emissão condicionada ao estado da matrícula e exportação em PDF oficial."""

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.audit.models import AuditLogEntry
from apps.enrollment.models import Enrollment
from apps.reports.models import IssuedDocument

pytestmark = pytest.mark.django_db

SELECTION_URL = reverse("enrollment:declaracao_selection")
PDF_URL = reverse("enrollment:declaracao_pdf")


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


def test_selection_forbidden_without_permission(institution, user_factory):
    guardian = user_factory(profile=Profile.GUARDIAN, institution=institution)
    client = Client()
    client.force_login(guardian)

    response = client.get(SELECTION_URL)

    assert response.status_code == 403


def test_selection_lists_enrolled_students(admin_client, enrollment, school_class):
    response = admin_client.get(SELECTION_URL, {"turma": str(school_class.id)})

    assert response.status_code == 200
    assert "Yolene Hangalo" in response.content.decode()


def test_declaracao_matricula_is_issued_for_any_status(admin_client, institution, enrollment):
    response = admin_client.post(
        PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-matricula"}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

    issued = IssuedDocument.all_objects.get(institution=institution)
    assert issued.document_type == "declaracao-matricula"


def test_declaracao_frequencia_rejected_for_cancelled_enrollment(
    admin_client, institution, enrollment
):
    enrollment.status = Enrollment.Status.CANCELLED
    enrollment.save()

    response = admin_client.post(
        PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-frequencia"}, follow=True
    )

    assert response.status_code == 200
    assert not IssuedDocument.all_objects.filter(institution=institution).exists()


def test_declaracao_conclusao_issued_for_completed_enrollment(
    admin_client, institution, enrollment
):
    enrollment.status = Enrollment.Status.COMPLETED
    enrollment.save()

    response = admin_client.post(
        PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-conclusao"}
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_declaracao_conclusao_rejected_for_active_enrollment(admin_client, institution, enrollment):
    response = admin_client.post(
        PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-conclusao"}, follow=True
    )

    assert response.status_code == 200
    assert not IssuedDocument.all_objects.filter(institution=institution).exists()


def test_pdf_export_is_forbidden_without_permission(institution, user_factory, enrollment):
    guardian = user_factory(profile=Profile.GUARDIAN, institution=institution)
    client = Client()
    client.force_login(guardian)

    response = client.post(
        PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-matricula"}
    )

    assert response.status_code == 403


def test_issuing_creates_an_audit_log_entry(admin_client, institution, enrollment):
    admin_client.post(PDF_URL, {"matricula": str(enrollment.id), "tipo": "declaracao-matricula"})

    issued = IssuedDocument.all_objects.get(institution=institution)
    entry = AuditLogEntry.objects.get(entity="reports.IssuedDocument", entity_id=str(issued.pk))
    assert entry.action == AuditLogEntry.Action.CREATE
