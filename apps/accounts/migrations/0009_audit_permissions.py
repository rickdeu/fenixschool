"""Grants view-only access to `audit.AuditLogEntry` to Super Administrador
and Administrador da Instituição (issue #140, docs/07-perfis-permissoes-e-
fluxos.md §7.2's "Auditoria" row: "L | L | — | — | — | — | — | — | —" --
every other profile gets none)."""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_ONLY = ("view",)

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {"audit": {"auditlogentry": VIEW_ONLY}},
    "Administrador da Instituição": {"audit": {"auditlogentry": VIEW_ONLY}},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("audit"), verbosity=0, using=schema_editor.connection.alias
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
        ("accounts", "0008_guardian_object_scoped_permissions"),
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
