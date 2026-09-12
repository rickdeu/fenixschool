"""
Definições de produção para o Nó Central (nuvem, multi-tenant).

PostgreSQL como base de dados, Celery + Redis para tarefas assíncronas (notificações em
massa, relatórios pesados) e o endpoint DRF de sincronização (`apps.api`) activo para
receber os Nós Locais.

Ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1/§10.3.
"""

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

# Production defaults to DEBUG=False regardless of what `base.py` fell back
# to -- only an explicit DJANGO_DEBUG=true in this node's `.env` turns it on.
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="fenixschool"),
        "USER": env("POSTGRES_USER", default="fenixschool"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
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
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE  # noqa: F405
