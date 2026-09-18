"""Tests for the automatic database backup (issue #166, RF-INST-*,
docs/11-implantacao-e-operacoes.md §11.4)."""

from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.core.services import backup_database

pytestmark = pytest.mark.django_db

POSTGRES_DATABASE = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "fenixschool",
        "USER": "fenixschool",
        "PASSWORD": "s3cret",
        "HOST": "db",
        "PORT": "5432",
    }
}


@override_settings(DATABASES=POSTGRES_DATABASE)
def test_backup_database_dumps_then_gzips_never_a_piped_command(tmp_path, monkeypatch):
    """A piped `pg_dump | gzip` would let a failing `pg_dump` still exit 0
    (gzip's own success) and silently produce an empty "successful" backup --
    see scripts/backup.sh's own comment for the same reasoning."""
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        class Result:
            returncode = 0

        if command[0] == "pg_dump":
            # Simulate pg_dump actually producing the file gzip expects next.
            dump_path = command[command.index("--file") + 1]
            open(dump_path, "w").close()
        return Result()

    with patch("apps.core.services.subprocess.run", side_effect=fake_run) as mock_run:
        result_path = backup_database()

    assert mock_run.call_count == 2
    assert calls[0][0] == "pg_dump"
    assert calls[1][0] == "gzip"
    # gzip's target must be the exact .sql file pg_dump wrote to, not the
    # already-appended-.gz result path.
    assert calls[1][-1] == str(result_path)[: -len(".gz")]
    assert result_path.name.startswith("fenixschool-")
    assert result_path.name.endswith(".sql.gz")


@override_settings(DATABASES=POSTGRES_DATABASE)
def test_backup_database_passes_connection_details_and_password_via_env(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

    def fake_run(command, **kwargs):
        if command[0] == "pg_dump":
            assert "--host" in command
            assert command[command.index("--host") + 1] == "db"
            assert command[command.index("--username") + 1] == "fenixschool"
            assert command[command.index("--dbname") + 1] == "fenixschool"
            assert kwargs["env"]["PGPASSWORD"] == "s3cret"
            dump_path = command[command.index("--file") + 1]
            open(dump_path, "w").close()

        class Result:
            returncode = 0

        return Result()

    with patch("apps.core.services.subprocess.run", side_effect=fake_run):
        backup_database()


@override_settings(DATABASES=POSTGRES_DATABASE)
def test_backup_database_creates_the_backup_dir_if_missing(tmp_path, monkeypatch):
    target = tmp_path / "does-not-exist-yet"
    monkeypatch.setenv("BACKUP_DIR", str(target))

    def fake_run(command, **kwargs):
        if command[0] == "pg_dump":
            dump_path = command[command.index("--file") + 1]
            open(dump_path, "w").close()

        class Result:
            returncode = 0

        return Result()

    with patch("apps.core.services.subprocess.run", side_effect=fake_run):
        backup_database()

    assert target.is_dir()
