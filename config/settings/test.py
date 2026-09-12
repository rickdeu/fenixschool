"""
Definições usadas pela suite de testes (`pytest` via `pytest-django`).

Optimizadas para velocidade e isolamento: SQLite em memória, hashers de palavra-passe
rápidos e envio de email para a caixa local (`locmem`). Ver `pyproject.toml`
(`[tool.pytest.ini_options]`) e docs/13-testes-e-qualidade.md.
"""

from .base import *  # noqa: F401,F403

DEBUG = False

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
