"""
Definições de produção para o Nó Central (nuvem, multi-tenant).

PostgreSQL como base de dados, Celery + Redis para tarefas assíncronas (notificações em
massa, relatórios pesados) e o endpoint DRF de sincronização (`apps.api`) activo para
receber os Nós Locais.

Ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1/§10.3.
"""

import logging

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

# Logs task start/success/failure/retry through the same structlog pipeline
# as everything else (config/settings/base.py's "Logging" section) -- only
# meaningful here: the local node has no Celery, only Django-Q, which
# django_structlog does not integrate with.
DJANGO_STRUCTLOG_CELERY_ENABLED = True

# Sentry (RNF-OBS-03, issue #14) -- reports application errors when there is
# connectivity, without ever blocking the local node's offline operation:
# `sentry-sdk` isn't even a dependency there (see requirements/local_node.txt
# vs requirements/central_node.txt), and here on the central node itself,
# `sentry_sdk.init()` only runs when a real SENTRY_DSN is configured -- an
# absent/blank one (the default) leaves error reporting off entirely, with no
# error and no effect on startup.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="central_node"),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            # Breadcrumbs from INFO+ log records, an actual Sentry event from
            # ERROR+ ones -- matches this node's own DJANGO_LOG_LEVEL default
            # (config/settings/base.py).
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        # No performance tracing by default -- this issue is about error
        # reporting only; a real deployment can opt in explicitly.
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        # These are minors' personal data (docs/09-seguranca-e-privacidade.md)
        # -- never send request bodies/user data to a third-party service by
        # default.
        send_default_pii=False,
    )
