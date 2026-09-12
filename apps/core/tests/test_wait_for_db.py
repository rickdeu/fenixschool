"""Tests for the `wait_for_db` management command (docker/entrypoint.sh)."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db.utils import OperationalError


@pytest.mark.django_db
def test_returns_immediately_when_the_database_is_already_up():
    out = StringIO()
    call_command("wait_for_db", stdout=out)

    assert "Database is available." in out.getvalue()


def test_retries_until_the_database_becomes_available():
    # `connections["default"].ensure_connection` raises twice, then succeeds.
    side_effects = [OperationalError("not ready"), OperationalError("not ready"), None]

    with (
        patch(
            "django.db.utils.ConnectionHandler.__getitem__",
        ) as get_connection,
        patch("time.sleep"),
    ):
        get_connection.return_value.ensure_connection.side_effect = side_effects
        out = StringIO()
        call_command("wait_for_db", interval=0, stdout=out)

    assert out.getvalue().count("Database unavailable, waiting...") == 2
    assert "Database is available." in out.getvalue()


def test_gives_up_after_the_timeout_elapses():
    with (
        patch(
            "django.db.utils.ConnectionHandler.__getitem__",
        ) as get_connection,
        patch("time.sleep"),
    ):
        get_connection.return_value.ensure_connection.side_effect = OperationalError(
            "still not ready"
        )

        with pytest.raises(OperationalError):
            call_command("wait_for_db", timeout=0, interval=0, stderr=StringIO())
