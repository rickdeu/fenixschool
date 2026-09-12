"""Tests for the central node's optional Sentry integration (issue #14, RNF-OBS-03).

Every check runs `config.settings.central_node` in its own subprocess:
`sentry_sdk.init()` sets process-wide global state, and this suite itself
already runs under `config.settings.test` (which has no Sentry setup at all).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# A syntactically valid (fake) DSN -- `sentry_sdk.init()` parses and stores
# it, but nothing here ever sends a real network request to Sentry.
_FAKE_DSN = "https://examplepublickey@o0.ingest.sentry.io/0"

_PRINT_SENTRY_STATE = (
    "import json\n"
    "import django\n"
    "django.setup()\n"
    "import sentry_sdk\n"
    "client = sentry_sdk.get_client()\n"
    "print(json.dumps({'active': client.is_active(), 'dsn': client.dsn}))\n"
)

_MINIMAL_CENTRAL_NODE_ENV = {
    # Only what config.settings.central_node needs to import cleanly outside
    # a real Postgres/Redis deployment -- these tests only care about the
    # Sentry setup, not the rest of the settings module.
    "DJANGO_SETTINGS_MODULE": "config.settings.central_node",
}


def _read_sentry_state(extra_env: dict[str, str]) -> dict:
    env = {**os.environ, **_MINIMAL_CENTRAL_NODE_ENV, **extra_env}
    result = subprocess.run(
        [sys.executable, "-c", _PRINT_SENTRY_STATE],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_no_dsn_leaves_sentry_inactive_with_no_error():
    state = _read_sentry_state({"SENTRY_DSN": ""})

    assert state["active"] is False


def test_a_configured_dsn_activates_sentry():
    state = _read_sentry_state({"SENTRY_DSN": _FAKE_DSN})

    assert state["active"] is True
    assert state["dsn"] == _FAKE_DSN


def test_local_node_settings_never_reference_sentry():
    local_node_settings = (BASE_DIR / "config" / "settings" / "local_node.py").read_text()
    local_node_requirements = (BASE_DIR / "requirements" / "local_node.txt").read_text()

    assert "sentry" not in local_node_settings.lower()
    assert "sentry" not in local_node_requirements.lower()
