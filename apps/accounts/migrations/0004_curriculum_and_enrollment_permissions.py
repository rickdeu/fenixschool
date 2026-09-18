"""Extends the profile Groups (issue #22's 0003_profile_groups) with the
"Currículo" and "Inscrição/Matrícula" rows of docs/07-perfis-permissoes-e-
fluxos.md §7.2, now that `academic` (issues #30-#35) and `enrollment`
(issues #39-#43) have real models.

Docente/Encarregado de Educação/Aluno's rows are qualified ("próprias
turmas"/"próprio(s)"/"próprio educando") -- object-level scoping isn't built
yet (issue #29), so granting them the blanket Django model permission now
would let them see *every* record, not just their own, which is not what the
matrix asks for. Left at their current permissions (empty, per 0003) on
purpose, same reasoning as that migration's own docstring -- issue #29 is
expected to extend them once object-level scoping exists.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_CRUD = ("add", "change", "delete", "view")
CREATE_VIEW_CHANGE = ("add", "change", "view")
VIEW_ONLY = ("view",)

CURRICULUM_MODELS = (
    "department",
    "course",
    "curricularyear",
    "subject",
    "room",
    "schoolclass",
)
ENROLLMENT_MODELS = (
    "student",
    "guardian",
    "studentguardian",
    "candidate",
    "enrollment",
)

# {group name: {app_label: {model_name: (actions...)}}} -- merged into (not
# replacing) each group's existing permissions from 0003_profile_groups.
NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {
        "academic": dict.fromkeys(CURRICULUM_MODELS, VIEW_ONLY),
        "enrollment": dict.fromkeys(ENROLLMENT_MODELS, VIEW_ONLY),
    },
    "Administrador da Instituição": {
        "academic": dict.fromkeys(CURRICULUM_MODELS, FULL_CRUD),
        "enrollment": dict.fromkeys(ENROLLMENT_MODELS, VIEW_ONLY),
    },
    "Direção Pedagógica": {
        "academic": dict.fromkeys(CURRICULUM_MODELS, CREATE_VIEW_CHANGE),
        "enrollment": dict.fromkeys(ENROLLMENT_MODELS, VIEW_ONLY),
    },
    "Secretaria Escolar": {
        "academic": dict.fromkeys(CURRICULUM_MODELS, VIEW_ONLY),
        "enrollment": dict.fromkeys(ENROLLMENT_MODELS, FULL_CRUD),
    },
    "Financeiro/Tesouraria": {
        "enrollment": dict.fromkeys(ENROLLMENT_MODELS, VIEW_ONLY),
    },
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    for app_label in ("academic", "enrollment"):
        create_permissions(
            global_apps.get_app_config(app_label),
            verbosity=0,
            using=schema_editor.connection.alias,
        )

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, permissions_by_app in NEW_PERMISSIONS_BY_GROUP.items():
        group = Group.objects.get(name=group_name)

        permission_ids: set[int] = set()
        for app_label, models in permissions_by_app.items():
            codenames = [
                codename
                for model_name, actions in models.items()
                for codename in _permission_codenames(model_name, actions)
            ]
            permission_ids.update(
                Permission.objects.filter(
                    content_type__app_label=app_label, codename__in=codenames
                ).values_list("id", flat=True)
            )
        # .add(), not .set(): extends this group's existing (core/sync)
        # permissions from 0003_profile_groups instead of replacing them.
        group.permissions.add(*permission_ids)


def revert_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, permissions_by_app in NEW_PERMISSIONS_BY_GROUP.items():
        group = Group.objects.get(name=group_name)
        for app_label, models in permissions_by_app.items():
            codenames = [
                codename
                for model_name, actions in models.items()
                for codename in _permission_codenames(model_name, actions)
            ]
            permission_ids = Permission.objects.filter(
                content_type__app_label=app_label, codename__in=codenames
            ).values_list("id", flat=True)
            group.permissions.remove(*permission_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_groups"),
        ("academic", "0001_initial"),
        ("enrollment", "0003_student_guardian_consent"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
