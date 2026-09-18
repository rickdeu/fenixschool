"""Tests for the accounts.0004_curriculum_and_enrollment_permissions migration
(§7.2's "Currículo" and "Inscrição/Matrícula" rows, extending issue #22's groups
now that `academic`/`enrollment` have real models)."""

import pytest
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db

CURRICULUM_MODELS = ("department", "course", "curricularyear", "subject", "room", "schoolclass")
ENROLLMENT_MODELS = ("student", "guardian", "studentguardian", "candidate", "enrollment")


def _codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions.values_list("codename", flat=True))


def test_super_admin_only_views_curriculum_and_enrollment():
    codenames = _codenames("Super Administrador")

    for model in (*CURRICULUM_MODELS, *ENROLLMENT_MODELS):
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))


def test_institution_administrator_has_full_crud_on_curriculum():
    codenames = _codenames("Administrador da Instituição")

    for model in CURRICULUM_MODELS:
        for action in ("add", "change", "delete", "view"):
            assert f"{action}_{model}" in codenames


def test_institution_administrator_only_views_enrollment():
    codenames = _codenames("Administrador da Instituição")

    for model in ENROLLMENT_MODELS:
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))


def test_pedagogical_direction_can_create_and_change_but_not_delete_curriculum():
    codenames = _codenames("Direção Pedagógica")

    for model in CURRICULUM_MODELS:
        assert f"add_{model}" in codenames
        assert f"change_{model}" in codenames
        assert f"view_{model}" in codenames
        assert f"delete_{model}" not in codenames


def test_extending_permissions_does_not_wipe_out_earlier_ones():
    """0004 uses .add(), not .set() -- must not clobber 0003's core/sync grants."""
    codenames = _codenames("Super Administrador")

    assert "add_institution" in codenames
    assert "add_node" in codenames
