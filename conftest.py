"""Configuração global de pytest para o projecto FenixSchool.

Nesta fase de fundação técnica (M0) ainda não existem testes — apenas a estrutura de
`tests/` e `apps/<app>/tests/` está criada (ver docs/13-testes-e-qualidade.md). Por
omissão, o pytest termina com o código de saída 5 ("no tests collected") quando nenhum
teste é encontrado, o que quebraria pipelines de CI nesta fase inicial. Este hook trata
esse caso específico como sucesso, sem mascarar falhas reais de testes.
"""

import pytest


def pytest_sessionfinish(session, exitstatus):
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
