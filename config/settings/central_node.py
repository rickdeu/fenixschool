"""
Definições de produção para o Nó Central (nuvem, multi-tenant).

PostgreSQL como base de dados, Celery + Redis para tarefas assíncronas (notificações em
massa, relatórios pesados) e o endpoint DRF de sincronização (`apps.api`) activo para
receber os Nós Locais.

Ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1/§10.3.
"""

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env_bool, env_list, os

DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "fenixschool"),
        "USER": os.environ.get("POSTGRES_USER", "fenixschool"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Celery + Redis — tarefas assíncronas do Nó Central (notificações em massa,
# relatórios pesados) — ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1.
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE  # noqa: F405
