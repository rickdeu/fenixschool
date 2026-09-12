"""
Base settings for the FenixSchool project, shared by every environment.

The concrete environments (`local_node`, `central_node`, `test`) import this module
and override only what is specific to their context (database, async task queue,
etc.) — see docs/10-stack-tecnologica-e-estrutura-projeto.md §10.2/§10.3.
"""

import os
from pathlib import Path

# BASE_DIR points at the repository root (two levels above this file:
# config/settings/base.py -> config/settings -> config -> root).
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable (accepts 1/0, true/false, yes/no)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    """Read a comma-separated environment variable as a list."""
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


# SECURITY WARNING: keep the secret key secret in production! Every production
# environment (local node / central node) MUST set DJANGO_SECRET_KEY in its
# `.env` -- this default is only acceptable for local development.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-fenixschool-dev-only-change-me-in-production",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", [])


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
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
