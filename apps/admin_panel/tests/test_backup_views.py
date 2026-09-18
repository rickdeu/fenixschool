"""Tests for the dedicated "Cópias de segurança" screen (issue #166)."""

import gzip
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin_panel:backup_list")


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


def test_requires_login(client):
    response = client.get(LIST_URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_requires_permission(institution):
    User.objects.create_user(
        username="prof1", institution=institution, profile=Profile.TEACHER, password="pw12345"
    )
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(LIST_URL)

    assert response.status_code == 403


def test_lists_existing_backups(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    (tmp_path / "fenixschool-20260101-000000.sql.gz").write_bytes(gzip.compress(b"dummy"))

    response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    assert len(response.context["backups"]) == 1
    assert response.context["backups"][0]["name"] == "fenixschool-20260101-000000.sql.gz"


def test_no_backups_yet_shows_the_empty_state(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "does-not-exist"))

    response = admin_client.get(LIST_URL)

    assert response.status_code == 200
    assert response.context["backups"] == []
    assert "Ainda não existe nenhuma cópia" in response.content.decode()


def test_run_now_triggers_a_real_backup(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

    with patch("apps.admin_panel.views.backup_view.backup_database") as mock_backup:
        response = admin_client.post(LIST_URL, {"run_now": "1"}, follow=True)

    mock_backup.assert_called_once()
    assert response.status_code == 200
    assert "criada com sucesso" in response.content.decode()


def test_download_an_existing_backup(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    content = gzip.compress(b"dummy dump")
    (tmp_path / "fenixschool-20260101-000000.sql.gz").write_bytes(content)

    response = admin_client.get(
        reverse("admin_panel:backup_download", args=["fenixschool-20260101-000000.sql.gz"])
    )

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == content


def test_download_rejects_path_traversal(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

    response = admin_client.get(reverse("admin_panel:backup_download", args=[".."]))

    assert response.status_code == 404


def test_download_rejects_a_file_that_is_not_a_backup(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    (tmp_path / "not-a-backup.txt").write_text("secret")

    response = admin_client.get(
        reverse("admin_panel:backup_download", args=["not-a-backup.txt"])
    )

    assert response.status_code == 404


def test_download_a_nonexistent_backup_404s(admin_client, tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))

    response = admin_client.get(
        reverse("admin_panel:backup_download", args=["fenixschool-missing.sql.gz"])
    )

    assert response.status_code == 404
