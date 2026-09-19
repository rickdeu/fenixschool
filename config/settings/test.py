"""
Definições usadas pela suite de testes (`pytest` via `pytest-django`).

Optimizadas para velocidade e isolamento: SQLite em memória, hashers de palavra-passe
rápidos e envio de email para a caixa local (`locmem`). Ver `pyproject.toml`
(`[tool.pytest.ini_options]`) e docs/13-testes-e-qualidade.md.
"""

import tempfile

from .base import *  # noqa: F401,F403

DEBUG = False

# Nunca o ficheiro real do repositório (`base.py`'s default) -- os testes de
# `setup_institution()`/`create_local_node()` (issue #123) não devem
# escrever uma chave a sério na árvore do projecto a cada corrida da suite.
NODE_PRIVATE_KEY_PATH = str(tempfile.gettempdir() + "/fenixschool-test-node-private-key.pem")

SECRET_KEY = "django-insecure-fenixschool-test-suite-only"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
