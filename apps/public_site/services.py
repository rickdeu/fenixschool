"""Regras de negócio e transações da app `public_site`.

Mantém a lógica de negócio fora de views/forms para facilitar reutilização (ex.: entre
views normais e endpoints de API) e testes unitários isolados.
"""

from apps.core.models import Institution


def get_the_institution() -> Institution | None:
    """The single Institution this node hosts, or `None` before the setup
    wizard has run (issue #17) -- this MVP's Nó Local architecture only
    ever has one (docs/04-arquitetura-tecnica.md §4.4.1), so there's no
    ambiguity to resolve, unlike `SyncedModel`'s per-request tenant
    context, which `Institution` itself deliberately has none of (it *is*
    the tenant).
    """
    return Institution.objects.first()
