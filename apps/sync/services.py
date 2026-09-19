"""Regras de negócio e transações da app `sync`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.

Issue #123 (RF-... 5.26/8.5): identidade própria de cada Nó Local -- uma chave
assimétrica (Ed25519, docs/08-offline-first-e-sincronizacao.md §8.5's "chave
assimétrica própria... mTLS ou token assinado") gerada uma única vez, na
instalação (ver `apps.core.services.setup_institution`), nunca reutilizada
entre nós -- cada instalação chama `create_local_node()` no máximo uma vez
(o próprio Setup Wizard só é acessível enquanto nenhuma `Institution` existir
ainda neste nó).
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings

from apps.core.context import get_current_node_id

from .models import Node


def generate_node_keypair() -> tuple[bytes, bytes]:
    """Um novo par de chaves Ed25519 (PEM), como `(chave_privada, chave_pública)`.

    Ed25519 (não RSA): assinaturas mais pequenas e mais rápidas de gerar/
    verificar para o volume de pedidos de sync (push/pull periódicos, §8.5) --
    a escolha idiomática moderna para "token assinado" quando não há já uma
    infra-estrutura PKI/mTLS existente a reaproveitar.
    """
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def create_local_node(*, institution) -> Node:
    """Cria o `Node` deste Nó Local, com uma chave própria acabada de gerar.

    A chave privada **nunca** entra na base de dados (`Node.public_key` só
    guarda a pública, tal como o próprio modelo já documenta) -- fica num
    ficheiro local (`settings.NODE_PRIVATE_KEY_PATH`), fora do controlo de
    versões (ver `.gitignore`) e fora de qualquer registo de sincronização,
    já que nunca deve sair deste nó.

    Chamado por `apps.core.services.setup_institution()` **depois** da sua
    própria transacção atómica ter sido confirmada -- escrever um ficheiro
    no disco não é uma operação transaccional com a base de dados, por isso
    fica deliberadamente fora do `transaction.atomic()` da criação da
    Instituição/Gestor, para nunca deixar um ficheiro de chave órfão se essa
    transacção for revertida.

    `Node.id` usa deliberadamente `get_current_node_id()` (em vez do
    `uuid7()` por omissão do próprio modelo): é o mesmo id que
    `SyncedModel.origin_node_id` já anda a usar neste processo (via
    `settings.NODE_ID`, ou o *fallback* aleatório por processo enquanto
    nenhum Node real existe) -- criar o registo com um id *diferente*
    deixaria todo o histórico de `ChangeRecord` já escrito a apontar para um
    node que, tecnicamente, nunca existiu. Persistir este id em
    `settings.NODE_ID`/`.env`, para que sobreviva a um reinício do
    processo, é um passo manual desta instalação por agora -- falta o
    registo real do Node junto do Nó Central (§11.3, M5) para automatizar
    isto de fio a pavio.
    """
    private_pem, public_pem = generate_node_keypair()

    key_path = Path(settings.NODE_PRIVATE_KEY_PATH)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(private_pem)
    key_path.chmod(0o600)

    return Node.objects.create(
        id=get_current_node_id(),
        node_type=Node.NodeType.LOCAL,
        institution=institution,
        public_key=public_pem.decode("ascii"),
    )
