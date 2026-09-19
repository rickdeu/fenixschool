"""Extends the profile Groups (issue #22's 0003_profile_groups) with
permissions for `reports.IssuedDocument` ("Documento Emitido"), now that
issue #93 has a real model.

§7.2's "Relatórios/Documentos" row: Super Admin=L, Admin Instituição=CLA,
Direção Pedagógica=CLA, Secretaria=CLA, Financeiro=CL (só financeiros --
âmbito ao nível de objecto ainda por implementar, mesmo raciocínio já usado
noutras permissões deste projecto). Sem "change"/"delete" para ninguém:
`IssuedDocument` é um registo histórico imutável (ver o próprio modelo) --
"criar" aqui significa emitir um novo documento através de
`apps.reports.services.emitir_documento`, nunca editar um já existente.

Docente não é incluído (mesmo tendo "L" na matriz): este projecto nunca
concede a esse grupo uma permissão Django genérica sem uma relação de
âmbito real já implementada (ver
`test_groups_without_a_matching_module_yet_start_with_no_permissions`) --
"os seus próprios documentos emitidos" só fará sentido quando #94/#96/#97
existirem, e aí sim precisará do mesmo tipo de scoping ao nível de objecto
já usado noutros sítios (ex. `Grade`/`Schedule`).
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

VIEW_ONLY = ("view",)
ADD_AND_VIEW = ("add", "view")

ISSUED_DOCUMENT_MODEL = "issueddocument"

NEW_PERMISSIONS_BY_GROUP = {
    "Super Administrador": {ISSUED_DOCUMENT_MODEL: VIEW_ONLY},
    "Administrador da Instituição": {ISSUED_DOCUMENT_MODEL: ADD_AND_VIEW},
    "Direção Pedagógica": {ISSUED_DOCUMENT_MODEL: ADD_AND_VIEW},
    "Secretaria Escolar": {ISSUED_DOCUMENT_MODEL: ADD_AND_VIEW},
    "Financeiro/Tesouraria": {ISSUED_DOCUMENT_MODEL: ADD_AND_VIEW},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def extend_group_permissions(apps, schema_editor):
    create_permissions(
        global_apps.get_app_config("reports"), verbosity=0, using=schema_editor.connection.alias
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
            content_type__app_label="reports", codename__in=codenames
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
            content_type__app_label="reports", codename__in=codenames
        ).values_list("id", flat=True)
        group.permissions.remove(*permission_ids)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_final_situation_permissions"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(extend_group_permissions, revert_group_permissions),
    ]
