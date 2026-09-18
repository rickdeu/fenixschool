"""Tests for the accounts.0009_audit_permissions migration (issue #140,
docs/07-perfis-permissoes-e-fluxos.md §7.2's "Auditoria" row)."""

import pytest
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db


def _codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions.values_list("codename", flat=True))


@pytest.mark.parametrize("group_name", ["Super Administrador", "Administrador da Instituição"])
def test_group_has_view_only_on_audit_log(group_name):
    codenames = _codenames(group_name)

    assert "view_auditlogentry" in codenames
    assert not any(
        f"{action}_auditlogentry" in codenames for action in ("add", "change", "delete")
    )


def test_no_other_group_can_see_the_audit_log():
    other_groups = [
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
    ]
    for group_name in other_groups:
        assert "view_auditlogentry" not in _codenames(group_name)
