"""Tests for structured request logging (issue #13, RNF-OBS-01).

`django_structlog.middlewares.RequestMiddleware` (config/settings/base.py's
`MIDDLEWARE`) logs a `request_started`/`request_finished` event per request;
`apps/core/signals.py` binds `institution_id`/`user_id` onto them. Captured
via `structlog.testing.capture_logs()` -- the officially recommended way to
assert on structlog output -- rather than reading the real rotated log file,
which stays untouched by the test suite.
"""

import pytest
import structlog.contextvars
import structlog.testing
from django.test import Client

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def _capture_requests():
    """`merge_contextvars` must be passed explicitly: `capture_logs` replaces
    the whole configured processor chain (including the one that would
    otherwise merge `apps/core/signals.py`'s bound `institution_id` in)."""
    return structlog.testing.capture_logs(processors=[structlog.contextvars.merge_contextvars])


def _events_named(entries, event_name):
    return [entry for entry in entries if entry.get("event") == event_name]


def test_anonymous_request_logs_started_and_finished_with_no_institution_or_user():
    with _capture_requests() as entries:
        response = Client().get("/admin/login/")

    assert response.status_code == 200
    (started,) = _events_named(entries, "request_started")
    (finished,) = _events_named(entries, "request_finished")
    assert started["institution_id"] is None
    assert started["user_id"] is None
    assert finished["code"] == 200
    assert finished["institution_id"] is None


def test_authenticated_request_binds_the_institution_and_user_id(institution_factory):
    institution = institution_factory("Escola do Log")
    user = User.objects.create_user(
        username="log-teacher",
        password="x",
        profile=Profile.TEACHER,
        institution=institution,
    )
    client = Client()
    client.force_login(user)

    with _capture_requests() as entries:
        client.get("/admin/")

    (finished,) = _events_named(entries, "request_finished")
    assert finished["user_id"] == str(user.id)
    assert finished["institution_id"] == str(institution.id)
