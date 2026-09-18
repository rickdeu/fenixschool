"""Tests for the accounts.0005_grading_formula_permissions migration (issue #18,
extending issue #22's groups now that `grading` has real models)."""

import pytest
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db

GRADING_MODELS = ("evaluationtype", "gradingformulaoverride")


def _codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions.values_list("codename", flat=True))


def test_institution_administrator_has_full_crud_on_grading_formula_config():
    codenames = _codenames("Administrador da Instituição")

    for model in GRADING_MODELS:
        for action in ("add", "change", "view"):
            assert f"{action}_{model}" in codenames
        assert f"delete_{model}" not in codenames


def test_pedagogical_direction_only_views_grading_formula_config():
    codenames = _codenames("Direção Pedagógica")

    for model in GRADING_MODELS:
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))


def test_super_admin_only_views_grading_formula_config():
    codenames = _codenames("Super Administrador")

    for model in GRADING_MODELS:
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))


def test_extending_permissions_does_not_wipe_out_earlier_ones():
    """0005 uses .add(), not .set() -- must not clobber earlier core/academic grants."""
    codenames = _codenames("Administrador da Instituição")

    assert "change_institution" in codenames
    assert "add_course" in codenames
