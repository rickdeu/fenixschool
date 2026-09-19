"""Cifra determinística de campo (issue #141, RNF-SEC-06/9.3): protege em
repouso os dados mais sensíveis (número de documento, contactos directos)
mesmo dentro da própria base de dados local/central.

**Determinística de propósito**, não aleatória (ao contrário de, por
exemplo, Fernet): o mesmo valor original cifra sempre para o mesmo texto
cifrado com a mesma chave. É a única forma de continuar a suportar
`.filter(campo=valor)`/`UniqueConstraint` de forma transparente, sem alterar
nenhuma lógica de negócio existente (RF-141's próprio critério de
aceitação) -- o preço é que dois registos com o mesmo valor original têm o
mesmo texto cifrado (uma fuga de igualdade, não do valor em si), aceitável
para o modelo de ameaça de "roubo do ficheiro da base de dados/backup", não
para resistir a análise de frequência sofisticada.

AES-SIV (RFC 5297, via `cryptography.hazmat.primitives.ciphers.aead.AESSIV`)
é o algoritmo escolhido exactamente por ser uma cifra autenticada
*desenhada* para ser usada de forma determinística com segurança (ao
contrário de, por exemplo, AES-ECB) -- ver
docs/09-seguranca-e-privacidade.md §9.3.
"""

import base64

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from django.conf import settings


def _cipher() -> AESSIV:
    key = base64.b64decode(settings.FIELD_ENCRYPTION_KEY)
    return AESSIV(key)


def encrypt_deterministic(value: str) -> str:
    """`value` -- em claro -- para o texto cifrado (base64 URL-safe) guardado
    na base de dados. Uma string vazia fica vazia (nunca cifrada): campos
    `blank=True` (ex. `Guardian.mobile_phone`) não perdem essa semântica."""
    if not value:
        return value
    ciphertext = _cipher().encrypt(value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(ciphertext).decode("ascii")


def decrypt_deterministic(value: str) -> str:
    """O inverso de `encrypt_deterministic` -- lido de volta da base de
    dados para o valor em claro que a aplicação espera."""
    if not value:
        return value
    ciphertext = base64.urlsafe_b64decode(value.encode("ascii"))
    return _cipher().decrypt(ciphertext, None).decode("utf-8")


def encrypted_max_length(plaintext_max_length: int) -> int:
    """A largura da coluna `varchar` necessária para guardar o texto cifrado
    de um valor em claro com `plaintext_max_length` caracteres -- sempre
    maior que o original (tag de autenticação do AES-SIV + codificação
    base64), nunca serve para validar o comprimento do valor em claro em si
    (isso continua a ser feito pelo `max_length` lógico do próprio campo,
    ver `apps.core.fields.EncryptedFieldMixin`)."""
    raw_length = plaintext_max_length + 16  # AES-SIV's synthetic IV/tag.
    base64_length = -(-raw_length // 3) * 4  # base64: ceil(n/3)*4 chars.
    return base64_length + 8  # small safety margin.
