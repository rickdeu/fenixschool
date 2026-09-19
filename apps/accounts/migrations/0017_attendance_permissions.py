"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `attendance.Attendance` ("Presença"), now that issue #65
has a real model.

§7.2's "Frequência" row: Super Admin=L, Admin Instituição=L, Direção
Pedagógica=LA, Secretaria=L, Financeiro=--, RH=--, Docente=CLA (próprias
turmas), Enc. Educação=L (próprio educando), Aluno=L (próprio). Docente/
Enc. Educação/Aluno are deliberately left out here, same reasoning as
`0013_grade_permissions`: a blanket Django permission would let them see/
mark attendance for every student at the institution, not just their own
scope -- issue #66 (docente marking, via `academic.Schedule` object-level
scoping, the same `@docente_required` pattern as `grading.Grade`) and #69
(mapa de faltas, Guardian's own `for_guardian`-style scoping) are expected
to extend these groups once that scoping exists in code, not here.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_ONLY = ("view",)
VIEW_AND_CHANGE = ("view", "change")

ATTENDANCE_MODEL = "attendance"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {ATTENDANCE_MODEL: VIEW_ONLY},
    "Administrador da Instituição": {ATTENDANCE_MODEL: VIEW_ONLY},
    "Direção Pedagógica": {ATTENDANCE_MODEL: VIEW_AND_CHANGE},
    "Secretaria Escolar": {ATTENDANCE_MODEL: VIEW_ONLY},
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
        ("accounts", "0016_issued_document_permissions"),
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
