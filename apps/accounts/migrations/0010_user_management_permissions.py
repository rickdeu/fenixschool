"""Grants `accounts.User` management permissions to Super Administrador
(full CRUD) and Administrador da Instituição (add/change/view, never
delete -- accounts are deactivated via `is_active`, never truly deleted,
matching the rest of this project's soft-management convention) -- issue
#113, RF-ADM-01.

The §7.2 permission matrix has no explicit "Utilizadores/Perfis" row
(0004's own docstring already noted this) -- this issue is exactly what
closes that gap, so these permissions are granted here rather than folded
into an earlier migration for a row that didn't exist yet.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_CRUD = ("add", "change", "delete", "view")
CREATE_VIEW_CHANGE = ("add", "change", "view")

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {"accounts": {"user": FULL_CRUD}},
    "Administrador da Instituição": {"accounts": {"user": CREATE_VIEW_CHANGE}},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("accounts"), verbosity=0, using=schema_editor.connection.alias
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
        ("accounts", "0009_audit_permissions"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
