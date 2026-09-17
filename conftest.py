"""Configuração global de pytest para o projecto FenixSchool.

Também expõe as fixtures comuns partilhadas por `apps/<app>/tests/` e por
`tests/` (ver docs/13-testes-e-qualidade.md §13.1): uma instituição de teste e
uma fábrica de utilizadores para qualquer perfil (docs/07-perfis-permissoes-e-
fluxos.md §7.1), construídas a partir das `factory_boy` factories de cada app
(`apps/core/factories.py`, `apps/accounts/factories.py`).
"""

import pytest

from apps.accounts.factories import UserFactory
from apps.accounts.models import Profile
from apps.core.factories import InstitutionFactory


def pytest_sessionfinish(session, exitstatus):
    # Por omissão, o pytest termina com o código de saída 5 ("no tests
    # collected") quando nenhum teste é encontrado por uma dada selecção
    # (por exemplo, `pytest apps/some_app_still_empty`), o que quebraria
    # pipelines de CI para apps ainda por implementar. Este hook trata esse
    # caso específico como sucesso, sem mascarar falhas reais de testes.
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK


@pytest.fixture
def institution(db):
    """A single test `Institution`, for tests that only need one tenant."""
    return InstitutionFactory()


@pytest.fixture
def user_factory(db):
    """Return a factory function for a `User` of any profile/institution.

    Example: ``user_factory(profile=Profile.TEACHER, institution=institution)``.
    """

    def _create(*, profile=Profile.INSTITUTION_ADMIN, institution=None, **kwargs):
        return UserFactory(profile=profile, institution=institution, **kwargs)

    return _create
