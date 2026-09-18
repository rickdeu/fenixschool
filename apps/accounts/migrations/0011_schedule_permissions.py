"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `academic.Schedule` ("Horário"), now that issue #36 has a
real model.

RF-CURR-06 groups Horário under "Gestão Curricular" alongside the other
`academic` models already covered by 0004_curriculum_and_enrollment_
permissions -- granted the exact same way (full CRUD for Administrador da
Instituição, create/view/change for Direção Pedagógica, view-only for
Super Administrador and Secretaria Escolar) rather than inventing a
different scheme just for this one model.

Docente/Diretor de Turma's own object-scoped view of *their* schedule
(issue #29's still-open "docente→turmas" half) is deliberately not granted
here: that needs a `for_docente(user)`-style scoped queryset, not a blanket
`view_schedule` a teacher could use to see every other teacher's timetable
too -- left to whichever issue actually builds that scoping.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_CRUD = ("add", "change", "delete", "view")
CREATE_VIEW_CHANGE = ("add", "change", "view")
VIEW_ONLY = ("view",)

SCHEDULE_MODEL = "schedule"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {SCHEDULE_MODEL: VIEW_ONLY},
    "Administrador da Instituição": {SCHEDULE_MODEL: FULL_CRUD},
    "Direção Pedagógica": {SCHEDULE_MODEL: CREATE_VIEW_CHANGE},
    "Secretaria Escolar": {SCHEDULE_MODEL: VIEW_ONLY},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("academic"), verbosity=0, using=schema_editor.connection.alias
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
            content_type__app_label="academic", codename__in=codenames
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
            content_type__app_label="academic", codename__in=codenames
        ).values_list("id", flat=True)
        group.permissions.remove(*permission_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_user_management_permissions"),
        ("academic", "0002_schedule"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
