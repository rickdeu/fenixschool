"""Tests for `apps.sync.services` (issue #123, RF-.../5.26 §8.5): a chave
própria de cada Node, gerada uma única vez na instalação, nunca reutilizada
entre nós."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.test import override_settings

from apps.core.context import get_current_node_id
from apps.sync.models import Node
from apps.sync.services import create_local_node, generate_node_keypair

pytestmark = pytest.mark.django_db


def test_generate_node_keypair_returns_a_usable_ed25519_pair():
    private_pem, public_pem = generate_node_keypair()

    private_key = serialization.load_pem_private_key(private_pem, password=None)
    public_key = serialization.load_pem_public_key(public_pem)
    assert isinstance(public_key, Ed25519PublicKey)

    message = b"fenixschool-sync-test"
    signature = private_key.sign(message)
    public_key.verify(signature, message)  # não levanta excepção -- assinatura válida.


def test_two_generated_keypairs_are_never_the_same():
    first_private, first_public = generate_node_keypair()
    second_private, second_public = generate_node_keypair()

    assert first_private != second_private
    assert first_public != second_public


def test_create_local_node_creates_a_local_node_with_a_public_key(institution, tmp_path):
    key_path = tmp_path / "node_private_key.pem"
    with override_settings(NODE_PRIVATE_KEY_PATH=str(key_path)):
        node = create_local_node(institution=institution)

    assert node.node_type == Node.NodeType.LOCAL
    assert node.institution == institution
    assert node.public_key.startswith("-----BEGIN PUBLIC KEY-----")
    assert Node.objects.filter(pk=node.pk).exists()


def test_create_local_node_reuses_this_processs_current_node_id(institution, tmp_path):
    key_path = tmp_path / "node_private_key.pem"
    with override_settings(NODE_PRIVATE_KEY_PATH=str(key_path)):
        node = create_local_node(institution=institution)

    # Qualquer `ChangeRecord` já escrito neste processo (via
    # `SyncedModel.origin_node_id`) usa `get_current_node_id()` -- o Node
    # recém-criado tem de ter o mesmo id, ou esse histórico passaria a
    # apontar para um node que nunca existiu.
    assert node.id == get_current_node_id()


def test_create_local_node_writes_the_private_key_to_disk_with_restricted_permissions(
    institution, tmp_path
):
    key_path = tmp_path / "node_private_key.pem"
    with override_settings(NODE_PRIVATE_KEY_PATH=str(key_path)):
        create_local_node(institution=institution)

    assert key_path.exists()
    private_pem = key_path.read_bytes()
    assert private_pem.startswith(b"-----BEGIN PRIVATE KEY-----")
    # Só o dono pode ler/escrever -- uma chave privada nunca deve ficar
    # legível por qualquer outro utilizador/processo na mesma máquina.
    assert (key_path.stat().st_mode & 0o777) == 0o600
