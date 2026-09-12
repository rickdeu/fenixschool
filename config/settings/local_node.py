"""
Definições de produção para o Nó Local (servidor físico na escola).

PostgreSQL como base de dados, Django-Q2 para tarefas assíncronas (sem Redis, para
reduzir os serviços necessários num servidor modesto) e WhiteNoise para servir
estáticos sem depender de um Nginx já configurado.

Ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1/§10.3.
"""

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, env

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

INSTALLED_APPS = [*INSTALLED_APPS, "django_q"]

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

# Django-Q2: fila assíncrona local, com broker em base de dados (sem Redis) — ver
# docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1.
Q_CLUSTER = {
    "name": "fenixschool_local_node",
    "orm": "default",
    "workers": env.int("DJANGO_Q_WORKERS", default=2),
    "timeout": 90,
    "retry": 120,
    "catch_up": False,
}
