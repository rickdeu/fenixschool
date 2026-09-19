"""Campos de modelo com cifra determinística em repouso (issue #141) --
ver `apps.core.crypto` para o porquê de ser determinística."""

from django.db import models

from .crypto import decrypt_deterministic, encrypt_deterministic, encrypted_max_length


class EncryptedFieldMixin:
    """`get_prep_value`/`from_db_value` cifram e decifram de forma
    transparente para o resto da aplicação: `.filter(campo=valor)`,
    `UniqueConstraint`, formulários e `full_clean()` continuam a ver sempre
    o valor em claro (é o que chega/sai da base de dados que muda) --
    RF-141's "leitura/escrita transparente... sem alterar lógica de
    negócio".

    `to_python` não decifra propositadamente: só é chamado com valores já
    em claro (atribuição em Python, formulários) -- os únicos valores
    cifrados que a aplicação alguma vez vê são os que vêm de `from_db_value`,
    nunca de uma atribuição normal.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_deterministic(value) if value else value

    def from_db_value(self, value, expression, connection):
        return decrypt_deterministic(value) if value else value

    def db_type(self, connection):
        # A largura física da coluna tem de caber o texto cifrado (sempre
        # maior que o original) -- `self.max_length` continua a validar o
        # comprimento do valor em claro (via `MaxLengthValidator`), nunca a
        # largura real da coluna.
        return f"varchar({encrypted_max_length(self.max_length)})"


class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    pass


class EncryptedEmailField(EncryptedFieldMixin, models.EmailField):
    pass
