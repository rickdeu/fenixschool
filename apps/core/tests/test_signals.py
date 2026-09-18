"""Tests for `apps.core.signals` (aside from the request-logging binding,
which is covered indirectly by the logging tests)."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from apps.core.signals import schedule_automatic_backup

pytestmark = pytest.mark.django_db


def test_does_nothing_when_django_q_is_not_installed():
    """The real state under every settings module except local_node's --
    see the signal's own docstring."""
    with patch("apps.core.signals.django_apps.is_installed", return_value=False):
        # Must not raise, and must never attempt the django_q import.
        schedule_automatic_backup(sender=None)


def test_registers_a_daily_schedule_when_django_q_is_installed():
    fake_schedule_model = MagicMock()
    fake_module = ModuleType("django_q.models")
    fake_module.Schedule = fake_schedule_model
    fake_schedule_model.DAILY = "D"

    with (
        patch("apps.core.signals.django_apps.is_installed", return_value=True),
        patch.dict(sys.modules, {"django_q.models": fake_module}),
    ):
        schedule_automatic_backup(sender=None)

    fake_schedule_model.objects.get_or_create.assert_called_once_with(
        func="apps.core.services.backup_database",
        defaults={
            "name": "Cópia de segurança diária da base de dados",
            "schedule_type": "D",
        },
    )
