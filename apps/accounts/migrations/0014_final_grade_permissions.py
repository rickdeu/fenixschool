"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `grading.FinalGrade` ("Média Final"), now that issue #58
has a real model.

Docente/Diretor de Turma deliberately get **no** permission here yet, same
reasoning as 0013_grade_permissions's own docstring: object-level scoping
(issue #29's still-open "docente→turmas" half) has to exist first, so a
blanket permission isn't fabricated ahead of it.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_CRUD = ("add", "change", "delete", "view")
CREATE_VIEW_CHANGE = ("add", "change", "view")
VIEW_ONLY = ("view",)

FINAL_GRADE_MODEL = "finalgrade"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {FINAL_GRADE_MODEL: VIEW_ONLY},
    "Administrador da Instituição": {FINAL_GRADE_MODEL: FULL_CRUD},
    "Direção Pedagógica": {FINAL_GRADE_MODEL: CREATE_VIEW_CHANGE},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("grading"), verbosity=0, using=schema_editor.connection.alias
    )

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, models in NEW_PERMISSIONS_BY_GROUP.items():
        group = Group.objects.get(name=group_name)
        codenames = [
            codename
            for model_name, actions in models.items()
            for codename in _permission_codenames(model_name, actions)
        ]
        permission_ids = Permission.objects.filter(
            content_type__app_label="grading", codename__in=codenames
        ).values_list("id", flat=True)
        # .add(), not .set(): extends this group's existing permissions
        # instead of replacing them.
        group.permissions.add(*permission_ids)


def revert_group_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name, models in NEW_PERMISSIONS_BY_GROUP.items():
        group = Group.objects.get(name=group_name)
        codenames = [
            codename
            for model_name, actions in models.items()
            for codename in _permission_codenames(model_name, actions)
        ]
        permission_ids = Permission.objects.filter(
            content_type__app_label="grading", codename__in=codenames
        ).values_list("id", flat=True)
        group.permissions.remove(*permission_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_grade_permissions"),
        ("grading", "0004_finalgrade"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
