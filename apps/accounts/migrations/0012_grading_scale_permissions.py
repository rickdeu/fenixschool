"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `grading.GradingScale` ("Escala de Avaliação"), now that
issue #56 has a real model.

Unlike every other `grading` model, this one is national reference data, not
a per-institution business record (see the model's own docstring) --
editable only by the Super Administrador (issue #56's acceptance criterion),
the same treatment `0003_profile_groups`'s `CORE_REFERENCE_MODELS` already
gives `core.Province`/`core.IdentificationDocumentType`/etc.: full CRUD for
Super Administrador, view-only for everyone who might reasonably need to
read it (Administrador da Instituição/Direção Pedagógica, to see the
qualitative level alongside a numeric grade once pautas/boletins exist).
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

FULL_CRUD = ("add", "change", "delete", "view")
VIEW_ONLY = ("view",)

GRADING_SCALE_MODEL = "gradingscale"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {GRADING_SCALE_MODEL: FULL_CRUD},
    "Administrador da Instituição": {GRADING_SCALE_MODEL: VIEW_ONLY},
    "Direção Pedagógica": {GRADING_SCALE_MODEL: VIEW_ONLY},
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
        ("accounts", "0011_schedule_permissions"),
        ("grading", "0002_gradingscale"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
