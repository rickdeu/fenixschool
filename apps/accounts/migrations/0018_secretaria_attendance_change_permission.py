"""Extends "Secretaria Escolar" with `change_attendance` (issue #67,
RF-FREQ-02).

`0017_attendance_permissions` granted Secretaria only view access,
following §7.2's "Frequência" row literally (L). Issue #67's own module
description (docs/06-modulos-e-funcionalidades.md §6.13, "Pedidos ao
secretariado (justificação de falta...) -- processamento final manual pela
Secretaria") is more specific about this one action: a Guardian's
justification *request* (via `guardian_portal`, not built by this issue)
is only ever actually applied to the `Attendance` row by the Secretaria --
so this group needs `change_attendance` too, not just `view_attendance`.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_AND_CHANGE = ("view", "change")

ATTENDANCE_MODEL = "attendance"

NEW_PERMISSIONS_BY_GROUP = {
    "Secretaria Escolar": {ATTENDANCE_MODEL: VIEW_AND_CHANGE},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("attendance"), verbosity=0, using=schema_editor.connection.alias
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
            content_type__app_label="attendance", codename__in=codenames
        ).values_list("id", flat=True)
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
            content_type__app_label="attendance", codename__in=codenames
        ).values_list("id", flat=True)
        group.permissions.remove(*permission_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0017_attendance_permissions"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
