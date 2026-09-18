"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `grading.EvaluationType`/`GradingFormulaOverride`, now that
issue #18 (fórmula de cálculo de média, RF-INST-06) has real models.

These two models are configuration parameters (RF-INST-06 sits under
"Instituição/Config." in docs/07-perfis-permissoes-e-fluxos.md §7.2, not
under that matrix's separate "Notas" row, which is about the `Nota`/grade
entity itself -- not built yet), so they're granted the same way as
`core.Institution`: full edit for the Administrador da Instituição, view-only
for Direção Pedagógica and the Super Administrador.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

CREATE_VIEW_CHANGE = ("add", "change", "view")
VIEW_ONLY = ("view",)

GRADING_MODELS = ("evaluationtype", "gradingformulaoverride")

# {group name: {model_name: (actions...)}} -- merged into (not replacing)
# each group's existing permissions from 0003/0004.
NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": dict.fromkeys(GRADING_MODELS, VIEW_ONLY),
    "Administrador da Instituição": dict.fromkeys(GRADING_MODELS, CREATE_VIEW_CHANGE),
    "Direção Pedagógica": dict.fromkeys(GRADING_MODELS, VIEW_ONLY),
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
        ("accounts", "0004_curriculum_and_enrollment_permissions"),
        ("grading", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
