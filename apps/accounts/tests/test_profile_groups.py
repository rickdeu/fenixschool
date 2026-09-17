"""Tests for the 12 profile Groups (issue #22, docs/07-perfis-permissoes-e-fluxos.md
§7.1-7.2). These rows come from the `accounts.0003_profile_groups` migration itself,
not any test fixture -- every test database goes through it, same as
`apps/core/tests/test_reference_data.py`."""

import pytest
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db

ALL_GROUP_NAMES = {
    "Super Administrador",
    "Administrador da Instituição",
    "Direção Pedagógica",
    "Secretaria Escolar",
    "Financeiro/Tesouraria",
    "Recursos Humanos",
    "Docente",
    "Diretor de Turma",
    "Biblioteca",
    "Encarregado de Educação",
    "Aluno",
    "Público",
}


def _codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions.values_list("codename", flat=True))


def test_all_12_profile_groups_exist():
    assert set(Group.objects.values_list("name", flat=True)) == ALL_GROUP_NAMES


def test_super_admin_has_full_crud_on_institution_and_sync():
    codenames = _codenames("Super Administrador")

    for action in ("add", "change", "delete", "view"):
        assert f"{action}_institution" in codenames
        assert f"{action}_node" in codenames
        assert f"{action}_changerecord" in codenames
        assert f"{action}_syncsession" in codenames


def test_institution_administrator_cannot_add_or_delete_the_institution_itself():
    codenames = _codenames("Administrador da Instituição")

    assert "view_institution" in codenames
    assert "change_institution" in codenames
    assert "add_institution" not in codenames
    assert "delete_institution" not in codenames


def test_institution_administrator_has_full_crud_on_the_academic_calendar():
    codenames = _codenames("Administrador da Instituição")

    for model in ("academicyear", "academicterm", "academiccycle", "nonteachingday"):
        for action in ("add", "change", "delete", "view"):
            assert f"{action}_{model}" in codenames


def test_institution_administrator_only_views_sync_state():
    codenames = _codenames("Administrador da Instituição")

    assert "view_node" in codenames
    assert "add_node" not in codenames
    assert "change_node" not in codenames
    assert "delete_node" not in codenames


def test_pedagogical_direction_is_read_only_on_institution_config():
    codenames = _codenames("Direção Pedagógica")

    assert "view_institution" in codenames
    assert "view_academicyear" in codenames
    assert not any(c.startswith(("add_", "change_", "delete_")) for c in codenames)


def test_pedagogical_direction_has_no_sync_access():
    codenames = _codenames("Direção Pedagógica")

    assert not any("node" in c or "changerecord" in c or "syncsession" in c for c in codenames)


@pytest.mark.parametrize(
    "group_name",
    [
        "Secretaria Escolar",
        "Financeiro/Tesouraria",
        "Recursos Humanos",
        "Docente",
        "Diretor de Turma",
        "Biblioteca",
        "Encarregado de Educação",
        "Aluno",
        "Público",
    ],
)
def test_groups_without_a_matching_module_yet_start_with_no_permissions(group_name):
    """These profiles' §7.2 rows are all in modules that don't exist yet
    (enrollment, grading, finance, ...) -- their own model-implementation
    issues are expected to extend these groups later."""
    assert _codenames(group_name) == set()
