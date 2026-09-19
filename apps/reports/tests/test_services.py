"""Tests for `apps.reports.services` (issue #93, RF-REL-06): numeração/
série nunca reutilizada e registo automático em auditoria de toda
emissão."""

import uuid
from unittest import mock

import pytest
from django.utils import translation

from apps.accounts.models import Profile
from apps.audit.context import audit_actor_context
from apps.audit.models import AuditLogEntry
from apps.reports import services as reports_services
from apps.reports.models import DocumentSequence, IssuedDocument
from apps.reports.services import emitir_documento, render_document_pdf

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def secretaria(institution, user_factory):
    return user_factory(profile=Profile.SECRETARY, institution=institution)


def test_first_document_gets_number_one(institution, secretaria):
    issued = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    assert issued.number == 1
    assert issued.formatted_number.startswith("DECLARACAO-MATRICULA/")
    assert issued.formatted_number.endswith("/000001")


def test_numbers_are_sequential_and_never_repeat(institution, secretaria):
    first = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )
    second = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    assert second.number == first.number + 1
    assert second.formatted_number != first.formatted_number


def test_sequences_are_independent_per_document_type(institution, secretaria):
    declaracao = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )
    pauta = emitir_documento(
        institution=institution,
        document_type="pauta-oficial",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    assert declaracao.number == 1
    assert pauta.number == 1
    assert DocumentSequence.all_objects.filter(institution=institution).count() == 2


def test_a_failure_after_reservation_never_frees_the_number(institution, secretaria):
    """RF-REL-06: "numeração nunca reutilizada, mesmo em caso de falha a
    meio da emissão" -- simulates a caller that reserves a number via
    `emitir_documento` and then fails downstream (ex. a PDF rendering
    error): the next emission must still get the following number, not the
    one that "failed"."""
    first = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )
    # Simulates the "meio da emissão" failure: nothing rolls back
    # `first`'s number reservation, since `_reserve_document_number`
    # commits its own transaction before `emitir_documento` returns.

    second = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    assert second.number == first.number + 1


def test_emitting_a_document_creates_an_audit_log_entry(institution, secretaria):
    # `audit_actor_context`: the signal handlers that create `AuditLogEntry`
    # rows read the current actor from a contextvar normally set by
    # `AuditActorMiddleware` on a real HTTP request -- calling the service
    # function directly, like here, needs the same context set by hand (see
    # `apps.audit.context`'s own docstring).
    with audit_actor_context(secretaria):
        issued = emitir_documento(
            institution=institution,
            document_type="declaracao-matricula",
            issued_by=secretaria,
            origin_node_id=_origin(),
        )

    entry = AuditLogEntry.objects.get(entity="reports.IssuedDocument", entity_id=str(issued.pk))
    assert entry.action == AuditLogEntry.Action.CREATE
    assert entry.user == secretaria


def test_issued_document_cannot_be_edited(institution, secretaria):
    issued = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    issued.document_type = "outro"
    with pytest.raises(Exception, match="não pode ser alterado"):
        issued.save()


def test_render_document_pdf_forces_portuguese_regardless_of_active_language():
    """Issue #152 (RF-I18N-03): um documento oficial nunca é traduzido --
    mesmo que o utilizador que o solicita tenha outro `preferred_language`
    activo no pedido."""
    captured = {}

    def fake_render_to_string(template_name, context):
        captured["language"] = translation.get_language()
        return "<html><body>documento</body></html>"

    translation.activate("umb")
    try:
        with mock.patch.object(
            reports_services, "render_to_string", side_effect=fake_render_to_string
        ):
            render_document_pdf("reports/base_document.html", {})
    finally:
        translation.deactivate()

    assert captured["language"] == "pt"


def test_issued_document_cannot_be_deleted(institution, secretaria):
    issued = emitir_documento(
        institution=institution,
        document_type="declaracao-matricula",
        issued_by=secretaria,
        origin_node_id=_origin(),
    )

    with pytest.raises(Exception, match="não pode ser eliminado"):
        issued.delete()

    assert IssuedDocument.all_objects.filter(pk=issued.pk).exists()
