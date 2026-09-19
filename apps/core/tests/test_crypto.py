"""Tests for `apps.core.crypto`/`apps.core.fields` (issue #141, RNF-SEC-06):
cifra determinística em repouso, transparente para a aplicação."""

import uuid

import pytest
from django.db import connection

from apps.core.context import tenant_context
from apps.core.crypto import decrypt_deterministic, encrypt_deterministic, encrypted_max_length
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian

pytestmark = pytest.mark.django_db


def test_encrypting_then_decrypting_returns_the_original_value():
    ciphertext = encrypt_deterministic("005LA00123")

    assert ciphertext != "005LA00123"
    assert decrypt_deterministic(ciphertext) == "005LA00123"


def test_encryption_is_deterministic():
    """A propriedade que torna `.filter(campo=valor)`/`UniqueConstraint`
    possíveis sobre um campo cifrado: o mesmo valor cifra sempre igual."""
    assert encrypt_deterministic("005LA00123") == encrypt_deterministic("005LA00123")


def test_different_values_encrypt_differently():
    assert encrypt_deterministic("005LA00123") != encrypt_deterministic("005LA00124")


def test_empty_string_is_never_encrypted():
    # Preserva a semântica de campos `blank=True` (ex.
    # `Guardian.mobile_phone`) -- uma string vazia continua vazia, nunca um
    # texto cifrado "vazio".
    assert encrypt_deterministic("") == ""
    assert decrypt_deterministic("") == ""


def test_encrypted_max_length_always_exceeds_the_plaintext_length():
    for plaintext_length in (1, 20, 50, 254):
        assert encrypted_max_length(plaintext_length) > plaintext_length


def test_guardian_document_number_is_encrypted_at_rest(institution):
    """Ponta-a-ponta: o texto guardado na base de dados nunca é o valor em
    claro, mas `Guardian.document_number` (via `from_db_value`) continua a
    devolver o original de forma transparente."""
    document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
    with tenant_context(institution.id):
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="CONSENT-000",
        )

    # `WHERE id = %s` is deliberately avoided here: SQLite (the test suite's
    # backend) stores `UUIDField` values as a 32-char hex string with no
    # dashes, unlike `str(uuid_obj)` -- fetching the single row this test
    # creates sidesteps that backend quirk entirely.
    with connection.cursor() as cursor:
        cursor.execute("SELECT document_number FROM enrollment_guardian")
        raw_value = cursor.fetchone()[0]

    assert raw_value != "CONSENT-000"
    guardian.refresh_from_db()
    assert guardian.document_number == "CONSENT-000"


def test_guardian_exact_match_filter_still_works_transparently(institution):
    """RF-141's próprio critério de aceitação: `.filter(document_number=...)`
    (usado em `student_inscription_view.py` para procurar um encarregado
    existente) continua a funcionar sem alterar nenhuma lógica de negócio."""
    document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
    with tenant_context(institution.id):
        Guardian.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="CONSENT-000",
        )

        found = Guardian.objects.filter(
            institution=institution, document_number="CONSENT-000"
        ).first()
        not_found = Guardian.objects.filter(
            institution=institution, document_number="OUTRO-VALOR"
        ).first()

    assert found is not None
    assert not_found is None
