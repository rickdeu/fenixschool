"""
Base settings for the FenixSchool project, shared by every environment.

The concrete environments (`local_node`, `central_node`, `test`) import this module
and override only what is specific to their context (database, async task queue,
etc.) — see docs/10-stack-tecnologica-e-estrutura-projeto.md §10.2/§10.3.
"""

from pathlib import Path

import environ
import structlog

# BASE_DIR points at the repository root (two levels above this file:
# config/settings/base.py -> config/settings -> config -> root).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# `env` is the single place every settings module (this one, `local_node`,
# `central_node`, `test`) reads configuration from -- see issue #12 and
# docs/09-seguranca-e-privacidade.md §9.7 ("segredos... geridos por variáveis
# de ambiente/`django-environ` e nunca commitados"). `.env.example`
# documents every variable it recognizes; a real `.env` (gitignored) is only
# read here for local development -- the node environments
# (local_node/central_node) get their environment from
# docker-compose.*.yml's own `env_file: .env` instead, so this call is a
# no-op there (the file simply doesn't exist inside the container image).
env = environ.Env(
    DJANGO_DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key secret in production! Every production
# environment (local node / central node) MUST set DJANGO_SECRET_KEY in its
# `.env` -- this default is only acceptable for local development.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-fenixschool-dev-only-change-me-in-production",
)

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    # Structured (JSON), locally-rotated logging (RNF-OBS-01) -- see the
    # "Logging" section below and docs/10-stack-tecnologica-e-estrutura-projeto.md
    # §10 (Observabilidade).
    "django_structlog",
    # Content-Security-Policy header -- see the "Security headers" section
    # below and docs/09-seguranca-e-privacidade.md §9.7 (issue #146).
    "csp",
]

# FenixSchool's own business apps -- see
# docs/10-stack-tecnologica-e-estrutura-projeto.md §10.2 for what each one is
# responsible for. The order roughly follows the dependencies between domains
# (core/accounts first; sync/audit/api last).
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.academic",
    "apps.enrollment",
    "apps.grading",
    "apps.attendance",
    "apps.finance",
    "apps.hr",
    "apps.communications",
    "apps.reports",
    "apps.public_site",
    "apps.student_portal",
    "apps.guardian_portal",
    "apps.admin_panel",
    "apps.sync",
    "apps.audit",
    "apps.api",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Resolves the current tenant (institution) from the authenticated user --
    # must run after AuthenticationMiddleware, which sets request.user. See
    # docs/04-arquitetura-tecnica.md §4.4.4 and apps/core/middleware.py.
    "apps.core.middleware.TenantMiddleware",
    # Binds request/user metadata (request_id, user_id...) to every log line
    # emitted while handling this request -- must run after
    # AuthenticationMiddleware and TenantMiddleware, which set request.user /
    # request.institution_id (bound in via apps/core/signals.py). See the
    # "Logging" section below.
    "django_structlog.middlewares.RequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Sets the Content-Security-Policy header on every response -- see the
    # "Security headers" section below (issue #146). Last, like Django's own
    # docs recommend, so it sees the final response the other middlewares
    # produced.
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
# Defaults to SQLite for zero-dependency local development (see
# docs/10-stack-tecnologica-e-estrutura-projeto.md §10.3). The node environments
# (local_node/central_node) override this with PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

# `EmailOrPhoneBackend` first (issue #24, docs/09-seguranca-e-privacidade.md
# §9.2: login by email/phone, never username) -- `ModelBackend` stays too, so
# username-based logins (the Django Admin's own login screen) keep working.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:landing_placeholder"

# This node's identity, once actually registered with the Central node
# (docs/11-implantacao-e-operacoes.md §11.3 -- not built yet). Left unset
# (the default) until then; see apps/core/context.py's get_current_node_id().
NODE_ID = env("NODE_ID", default="")


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization -- see docs/10-stack-tecnologica-e-estrutura-projeto.md §10.4
# NOTE: `accounts.User` will eventually get a `preferred_language` field that a thin
# custom middleware uses to activate the authenticated user's language before the
# standard LocaleMiddleware acts on anonymous users. That middleware is not part of
# this technical-foundation phase yet.

LANGUAGE_CODE = "pt"

LANGUAGES = [
    ("pt", "Português"),
    ("umb", "Umbundu"),
    ("kmb", "Kimbundu"),
    ("kon", "Kikongo"),
    ("cjk", "Chokwe"),
    ("kua", "Oshikwanyama"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Africa/Luanda"

USE_I18N = True

USE_TZ = True


# Static and media files
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework -- used only for the sync endpoints between the local
# node and the central node (`apps.api`), not as a general-purpose public API.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# Logging (RNF-OBS-01, issue #13) -- structured logs, rotated automatically,
# with no dependency on an external service (essential for the local node,
# which is expected to run fully offline). Every log line -- structlog's own
# calls (`structlog.get_logger(...)`) and plain stdlib ones (Django's own
# `django.request` etc.) alike -- ends up going through the same processor
# chain and out through the same handlers, rendered as JSON to a locally
# rotated file always, and additionally as human-readable text on the
# console while DEBUG is on. See docs/10-stack-tecnologica-e-estrutura-projeto.md
# §10 (Observabilidade) and apps/core/signals.py (binds request.institution_id
# from apps/core/middleware.py into every request's log lines).
LOG_DIR = Path(env("DJANGO_LOG_DIR", default=str(BASE_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# A structlog "foreign_pre_chain" -- applied only to *plain* stdlib
# `logging` records (structlog's own calls already went through
# `structlog.configure()`'s own `processors` below) so both end up with the
# same timestamp/level/contextvars shape before rendering.
_STRUCTLOG_FOREIGN_PRE_CHAIN = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": _STRUCTLOG_FOREIGN_PRE_CHAIN,
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                # Only DEBUG gets the coloured, human-oriented renderer --
                # every real deployment (local_node/central_node, DEBUG=False)
                # gets JSON on the console too, so a container's own log
                # driver (e.g. `docker logs`, journald) captures structured
                # lines from day one, with no separate configuration.
                structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": _STRUCTLOG_FOREIGN_PRE_CHAIN,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "fenixschool.log"),
            "when": "midnight",
            "backupCount": env.int("DJANGO_LOG_RETENTION_DAYS", default=30),
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Hands off to `logging`'s own dictConfig-configured handlers/
        # formatters (above) instead of structlog rendering the event
        # itself -- this is what lets structlog-native and plain stdlib log
        # records share one JSON file.
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


# Security headers (issue #146, docs/09-seguranca-e-privacidade.md §9.7).
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# TLS is provisioned per node via Nginx (self-signed certificate on the
# school's LAN for the local node, a public certificate on the central node --
# docs/09-seguranca-e-privacidade.md §9.3), not by Django itself, and is not
# wired up by default -- it needs docker-compose.tls.yml layered on top of the
# node's own compose file, plus a real certificate (see
# docs/11-implantacao-e-operacoes.md §11.3.1, issue #142). The settings below
# only make sense once requests actually arrive over HTTPS, so each node opts
# in explicitly with `DJANGO_SECURE_SSL=true` in its own `.env` once that is
# active -- turning them on earlier would either redirect every request into a
# loop (nothing listening on 443 yet) or silently drop session/CSRF cookies
# (browsers refuse `Secure` cookies over plain HTTP).
if env.bool("DJANGO_SECURE_SSL", default=False):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Nginx (docker/nginx/app.conf.template) always sets X-Forwarded-Proto, even
# though it talks to Django over plain HTTP inside the Docker network -- this
# lets Django/`SECURE_SSL_REDIRECT` above tell a request actually arrived over
# HTTPS at the edge instead of redirecting it again.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Content-Security-Policy (django-csp). Every asset is vendorized locally
# (templates/base.html, docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1:
# no external CDN), so `'self'` covers scripts/styles/images/fonts. Alpine.js
# needs `'unsafe-eval'` for its expression evaluation (`x-data`, `x-on`, ...);
# revisit this if the project ever adopts Alpine's separate CSP-compliant
# build instead.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-eval'"],
        "style-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
    },
}
