"""Tests for how `config.settings.base` reads configuration (issue #12).

Every check here runs `config.settings.base` in its own subprocess, given a
fully explicit environment, rather than importing it in-process: Django
settings are only ever configured once per process, and this suite already
runs under `config.settings.test`. Using explicit values (never "whatever
`DJANGO_SECRET_KEY` happens to be unset") also means these tests behave the
same whether or not the machine running them has a real local `.env` --
`environ.Env.read_env()` never overrides a variable the environment already
has (see `config/settings/base.py`), so an explicit subprocess environment
always wins regardless.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_PRINT_SETTINGS = (
    "import json\n"
    "from config.settings import base\n"
    "print(json.dumps({\n"
    "    'SECRET_KEY': base.SECRET_KEY,\n"
    "    'DEBUG': base.DEBUG,\n"
    "    'ALLOWED_HOSTS': base.ALLOWED_HOSTS,\n"
    "}))\n"
)


def _read_settings(env: dict[str, str]) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PRINT_SETTINGS],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_explicit_env_vars_are_read_into_settings():
    env = {
        **os.environ,
        "DJANGO_SECRET_KEY": "test-secret-from-env",
        "DJANGO_DEBUG": "false",
        "DJANGO_ALLOWED_HOSTS": "example.com,www.example.com",
    }

    settings = _read_settings(env)

    assert settings["SECRET_KEY"] == "test-secret-from-env"
    assert settings["DEBUG"] is False
    assert settings["ALLOWED_HOSTS"] == ["example.com", "www.example.com"]


def test_debug_true_is_parsed_as_a_real_boolean_not_the_string_true():
    env = {**os.environ, "DJANGO_DEBUG": "true"}

    settings = _read_settings(env)

    assert settings["DEBUG"] is True
