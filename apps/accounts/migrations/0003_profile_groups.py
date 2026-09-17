"""Creates the 12 profile Groups (issue #22, docs/07-perfis-permissoes-e-fluxos.md
§7.1) and assigns the Django permissions the §7.2 matrix already lets us assign
today.

The §7.2 matrix has rows for modules that don't exist yet (Currículo, Notas,
Financeiro, RH, Comunicação, ...) -- Django permissions are auto-created per
*real, migrated* model, so a permission for e.g. `academic.add_curso` simply
does not exist yet and cannot be assigned. Only the "Instituição/Config."
(`core`) and "Sincronização" (`sync`) rows have real models today. Every other
group therefore starts with **no permissions** here on purpose -- each app's
own model-implementation issue (enrollment, grading, finance, ...) is expected
to extend the relevant group(s) with its new permissions once its models
land, rather than this single migration fabricating permissions for models
that don't exist.

Beyond the two matrix rows: "Instituição/Config." bundles both `Institution`
itself (Super Admin only for add/delete -- an institution is provisioned
once, via the setup wizard, not created ad-hoc by its own administrator) and
the calendar/reference sub-models, where the Institution Administrator's own
"Configura parâmetros locais" role (§7.1) does need full CRUD (RF-INST-03/
04/05/07 all say "o sistema deve permitir configurar"). This is a judgment
call the matrix's single row doesn't spell out by sub-model -- see
docs/implementation-decisions.md.

Permissions for accounts.User itself are deliberately not assigned here: the
matrix has no "Utilizadores/Perfis" row, and user-management permissions are
issue #23/#29's concern (tenant-scoped user creation, object-level scoping),
not something to guess at in this migration.

Uses `create_permissions()` directly (rather than relying on the
`post_migrate` signal) because that signal only fires *after* every
migration in this run has already applied -- relying on it here would mean
the very permissions this migration wants to assign (for models this same
`migrate` run just created) don't exist yet.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_NAMES = [
    "Super Administrador",
    "Administrador da Instituição",
    "Direção Pedagógica",
    "Secretaria Escolar",
    "Financeiro/Tesouraria",
    "Recursos Humanos",
    "Docente",
    "Diretor de Turma",
    "Biblioteca",
    "Encarregado de Educação",
    "Aluno",
    "Público",
]

FULL_CRUD = ("add", "change", "delete", "view")
VIEW_AND_CHANGE = ("view", "change")
VIEW_ONLY = ("view",)

CORE_REFERENCE_MODELS = (
    "province",
    "municipality",
    "mobileoperator",
    "identificationdocumenttype",
    "profession",
)
CORE_CALENDAR_MODELS = (
    "academicyear",
    "academicterm",
    "academiccycle",
    "nonteachingday",
)
SYNC_MODELS = ("node", "changerecord", "syncsession")

# {group name: {app_label: {model_name: (actions...)}}}
PERMISSIONS_BY_GROUP = {
    "Super Administrador": {
        "core": {
            "institution": FULL_CRUD,
            **dict.fromkeys(CORE_CALENDAR_MODELS, FULL_CRUD),
            **dict.fromkeys(CORE_REFERENCE_MODELS, FULL_CRUD),
        },
        "sync": dict.fromkeys(SYNC_MODELS, FULL_CRUD),
    },
    "Administrador da Instituição": {
        "core": {
            "institution": VIEW_AND_CHANGE,
            **dict.fromkeys(CORE_CALENDAR_MODELS, FULL_CRUD),
            **dict.fromkeys(CORE_REFERENCE_MODELS, VIEW_ONLY),
        },
        "sync": dict.fromkeys(SYNC_MODELS, VIEW_ONLY),
    },
    "Direção Pedagógica": {
        "core": {
            "institution": VIEW_ONLY,
            **dict.fromkeys(CORE_CALENDAR_MODELS, VIEW_ONLY),
            **dict.fromkeys(CORE_REFERENCE_MODELS, VIEW_ONLY),
        },
    },
    # Everyone below has no row overlap with a module that exists yet --
    # left empty on purpose (see module docstring).
    "Secretaria Escolar": {},
    "Financeiro/Tesouraria": {},
    "Recursos Humanos": {},
    "Docente": {},
    "Diretor de Turma": {},
    "Biblioteca": {},
    "Encarregado de Educação": {},
    "Aluno": {},
    "Público": {},
}


def _permission_codenames(model_name, actions):
    return [f"{action}_{model_name}" for action in actions]


def create_groups_and_permissions(apps, schema_editor):
    for app_label in ("core", "accounts", "sync"):
        create_permissions(
            global_apps.get_app_config(app_label),
            verbosity=0,
            using=schema_editor.connection.alias,
        )

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for group_name in GROUP_NAMES:
        group, _ = Group.objects.get_or_create(name=group_name)

        # Queried one app_label at a time (rather than one combined
        # `codename__in`/`app_label__in` filter) so a codename that happens
        # to repeat across two of this group's apps can never pull in the
        # wrong app's permission.
        permission_ids: set[int] = set()
        for app_label, models in PERMISSIONS_BY_GROUP[group_name].items():
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
        group.permissions.set(permission_ids)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUP_NAMES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_is_2fa_active_user_phone_and_more"),
        ("core", "0004_academicyear_academicterm_nonteachingday_and_more"),
        ("sync", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_groups_and_permissions, delete_groups),
    ]
