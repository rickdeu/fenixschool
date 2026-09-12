"""
Definições de produção para o Nó Local (servidor físico na escola).

PostgreSQL como base de dados, Django-Q2 para tarefas assíncronas (sem Redis, para
reduzir os serviços necessários num servidor modesto) e WhiteNoise para servir
estáticos sem depender de um Nginx já configurado.

Ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1/§10.3.
"""

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, env_bool, env_list, os

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
    "workers": int(os.environ.get("DJANGO_Q_WORKERS", "2")),
    "timeout": 90,
    "retry": 120,
    "catch_up": False,
}
