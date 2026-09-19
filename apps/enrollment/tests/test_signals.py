"""Tests for `apps.enrollment.signals` -- mirrors
`apps.core.tests.test_signals` for the same reasoning (Django-Q2 schedule
registration, only when installed)."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from apps.enrollment.signals import schedule_enrollment_activation

pytestmark = pytest.mark.django_db


def test_does_nothing_when_django_q_is_not_installed():
    with patch("apps.enrollment.signals.django_apps.is_installed", return_value=False):
        schedule_enrollment_activation(sender=None)


def test_registers_a_daily_schedule_when_django_q_is_installed():
    fake_schedule_model = MagicMock()
    fake_module = ModuleType("django_q.models")
    fake_module.Schedule = fake_schedule_model
    fake_schedule_model.DAILY = "D"

    with (
        patch("apps.enrollment.signals.django_apps.is_installed", return_value=True),
        patch.dict(sys.modules, {"django_q.models": fake_module}),
    ):
        schedule_enrollment_activation(sender=None)

    fake_schedule_model.objects.get_or_create.assert_called_once_with(
        func="apps.enrollment.services.activar_matriculas_do_ano_lectivo_em_curso",
        defaults={
            "name": "Activação diária de matrículas do ano lectivo em curso",
            "schedule_type": "D",
        },
    )
