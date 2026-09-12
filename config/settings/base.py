"""
Definições base do projecto FenixSchool, comuns a todos os ambientes.

Os ambientes concretos (`local_node`, `central_node`, `test`) importam este módulo e
sobrepõem apenas o que é específico do seu contexto (base de dados, filas assíncronas,
etc.) — ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.2/§10.3.
"""

import os
from pathlib import Path

# BASE_DIR aponta para a raiz do repositório (dois níveis acima deste ficheiro:
# config/settings/base.py -> config/settings -> config -> raiz).
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool) -> bool:
    """Lê uma variável de ambiente booleana (aceita 1/0, true/false, yes/no)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    """Lê uma variável de ambiente como lista separada por vírgulas."""
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


# SECURITY WARNING: mantenha a chave secreta em segredo em produção! Cada ambiente de
# produção (Nó Local / Nó Central) DEVE definir DJANGO_SECRET_KEY no seu `.env` — este
# valor por omissão só é aceitável em desenvolvimento local.
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

# Apps de negócio do FenixSchool — ver docs/10-stack-tecnologica-e-estrutura-projeto.md
# §10.2 para a responsabilidade de cada uma. A ordem reflecte, grosso modo, as
# dependências entre domínios (core/accounts primeiro; sync/audit/api por último).
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


# Base de dados
# Por omissão usa-se SQLite para desenvolvimento sem dependências externas (ver
# docs/10-stack-tecnologica-e-estrutura-projeto.md §10.3). Os ambientes de nó
# (local_node/central_node) sobrepõem esta configuração com PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Validação de palavras-passe
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


# Internacionalização — ver docs/10-stack-tecnologica-e-estrutura-projeto.md §10.4
# NOTA: `accounts.Utilizador` (a implementar) terá o campo `idioma_preferido` que um
# middleware fino próprio usará para activar o idioma do utilizador autenticado antes do
# LocaleMiddleware standard actuar sobre utilizadores anónimos. Esse middleware ainda não
# existe nesta fase de fundação técnica (depende do modelo `accounts.Utilizador`).

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


# Ficheiros estáticos e media
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework — usado apenas para os endpoints de sincronização entre Nó
# Local e Nó Central (`apps.api`), não como API pública de aplicação.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
