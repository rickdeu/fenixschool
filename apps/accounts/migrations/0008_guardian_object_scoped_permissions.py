"""Grants "Encarregado de Educação" view access to `enrollment.Student`/
`Enrollment` (issue #29, docs/07-perfis-permissoes-e-fluxos.md §7.2's
"Inscrição/Matrícula" row: "L (próprio)"), now that `enrollment.Student`/
`Enrollment.objects.for_guardian(user)` (issue #29) exist to restrict this
to *their own* educandos.

Left empty by 0004 on purpose (that migration's own docstring: object-level
scoping wasn't built yet) -- Django's blanket `view_student`/`view_enrollment`
permission only gates "can this profile ever view these at all"; *which*
rows a Guardian actually sees is enforced by the queryset scoping itself,
in every view/service that serves them, not by this permission.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_ONLY = ("view",)

NEW_PERMISSIONS_BY_GROUP = {
    "Encarregado de Educação": {
        "enrollment": {
            "student": VIEW_ONLY,
            "enrollment": VIEW_ONLY,
        },
    },
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("enrollment"), verbosity=0, using=schema_editor.connection.alias
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
        # .add(), not .set(): extends this group's existing permissions
        # instead of replacing them.
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
        ("accounts", "0007_user_failed_login_attempts_user_locked_until_and_more"),
        ("enrollment", "0003_student_guardian_consent"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
