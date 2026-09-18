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
    """Read-only specifically on "Instituição/Config." -- §7.2's "Currículo"
    row (extended by accounts.0004) legitimately grants Direção Pedagógica
    add/change on academic curriculum models, just not on core config."""
    codenames = _codenames("Direção Pedagógica")

    assert "view_institution" in codenames
    assert "view_academicyear" in codenames
    core_codenames = set(
        Group.objects.get(name="Direção Pedagógica")
        .permissions.filter(content_type__app_label="core")
        .values_list("codename", flat=True)
    )
    assert not any(c.startswith(("add_", "change_", "delete_")) for c in core_codenames)


def test_pedagogical_direction_has_no_sync_access():
    codenames = _codenames("Direção Pedagógica")

    assert not any("node" in c or "changerecord" in c or "syncsession" in c for c in codenames)


@pytest.mark.parametrize(
    "group_name",
    [
        "Recursos Humanos",
        "Docente",
        "Diretor de Turma",
        "Biblioteca",
        "Aluno",
        "Público",
    ],
)
def test_groups_without_a_matching_module_yet_start_with_no_permissions(group_name):
    """These profiles' §7.2 rows are either in modules that don't exist yet
    (RH/finance/grading, ...) or are object-scoped ("próprias turmas"/
    "próprio") in a way that still needs a real relationship to scope by
    (e.g. Docente -- issues #36/#85, Turma/Horário/atribuição docente ainda
    não existem) -- granting the blanket Django permission now would be
    broader than the matrix actually intends. Their own follow-up issues
    are expected to extend these groups later. "Encarregado de Educação" is
    NOT included here any more: issue #29 built the real Guardian->Student
    relationship its object-level scoping needed (`StudentGuardian`), so its
    view-only grant already exists -- see
    `test_guardian_has_view_only_on_their_own_students_and_enrollments`.
    """
    assert _codenames(group_name) == set()


def test_guardian_has_view_only_on_their_own_students_and_enrollments():
    """issue #29: unlike Docente (still blocked on #36/#85), the Guardian
    scoping relationship (`enrollment.StudentGuardian`) already exists, so
    this group's blanket *view* permission is granted -- *which* rows a
    Guardian actually sees is enforced by
    `enrollment.services.get_students_for_guardian`/`get_enrollments_for_guardian`
    (`Student`/`Enrollment.objects.for_guardian(user)`), not by this
    permission, which only gates "can this profile ever view these"."""
    codenames = _codenames("Encarregado de Educação")

    assert codenames == {"view_student", "view_enrollment"}


def test_secretary_has_full_crud_on_enrollment_and_view_only_on_curriculum():
    codenames = _codenames("Secretaria Escolar")

    for model in ("student", "guardian", "studentguardian", "candidate", "enrollment"):
        for action in ("add", "change", "delete", "view"):
            assert f"{action}_{model}" in codenames
    for model in ("department", "course", "curricularyear", "subject", "room", "schoolclass"):
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))


def test_finance_only_views_enrollment_records():
    codenames = _codenames("Financeiro/Tesouraria")

    for model in ("student", "guardian", "studentguardian", "candidate", "enrollment"):
        assert f"view_{model}" in codenames
        assert not any(f"{action}_{model}" in codenames for action in ("add", "change", "delete"))
