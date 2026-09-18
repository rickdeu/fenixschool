"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `grading.FinalSituation` ("Situação Final"), now that issue
#62 has a real model.

View-only for every profile that gets it: the model itself has no add/change
permission at the `ModelAdmin` level either (see `FinalSituationAdmin`'s own
docstrings) -- it only ever exists via
`apps.grading.services.calcular_situacao_final`, triggered from
`EnrollmentAdmin`'s "Calcular situação final" action (gated on Enrollment's
own, already-existing change permission, not on this one).
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_ONLY = ("view",)

FINAL_SITUATION_MODEL = "finalsituation"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {FINAL_SITUATION_MODEL: VIEW_ONLY},
    "Administrador da Instituição": {FINAL_SITUATION_MODEL: VIEW_ONLY},
    "Direção Pedagógica": {FINAL_SITUATION_MODEL: VIEW_ONLY},
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
        ("accounts", "0014_final_grade_permissions"),
        ("grading", "0007_finalsituation"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
