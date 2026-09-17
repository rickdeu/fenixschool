"""Regras de negócio e transações da app `accounts`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from .models import User


def create_user(*, created_by: User, institution=None, **fields) -> User:
    """Create a `User`, propagating the tenant automatically (issue #23,
    docs/04-arquitetura-tecnica.md §4.4.1).

    The Super Administrator is the **only** profile that picks `institution`
    explicitly -- every other creator's new user always inherits
    `created_by.institution`, regardless of what (if anything) is passed as
    `institution`, so an ordinary "register a colleague" form never even
    needs an "Escola" field to begin with.
    """
    if created_by.is_super_admin:
        if institution is None:
            raise ValueError("institution is required when created_by is a Super Administrator.")
    else:
        institution = created_by.institution

    return User.objects.create_user(
        institution=institution,
        created_by=created_by,
        **fields,
    )
