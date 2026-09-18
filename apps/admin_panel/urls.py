"""Rotas da app `admin_panel`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    # -- Utilizadores/perfis (RF-ADM-01, issue #113) ----------------------------
    path("utilizadores/", views.user_list_view, name="user_list"),
    path("utilizadores/novo/", views.user_create_view, name="user_create"),
    path("utilizadores/<uuid:user_id>/editar/", views.user_edit_view, name="user_edit"),
    # -- Configuração da instituição (RF-ADM-02, issue #114) --------------------
    path("configuracao/", views.institution_config_view, name="institution_config"),
    path("configuracao/dados/", views.institution_edit_view, name="institution_edit"),
    # -- Anos lectivos e períodos (RF-INST-03/04, issue #16) --------------------
    path(
        "configuracao/anos-lectivos/",
        views.academic_year_list_view,
        name="academic_year_list",
    ),
    path(
        "configuracao/anos-lectivos/novo/",
        views.academic_year_create_view,
        name="academic_year_create",
    ),
    path(
        "configuracao/anos-lectivos/<uuid:academic_year_id>/editar/",
        views.academic_year_edit_view,
        name="academic_year_edit",
    ),
    path(
        "configuracao/anos-lectivos/<uuid:academic_year_id>/periodos/novo/",
        views.academic_term_create_view,
        name="academic_term_create",
    ),
    path(
        "configuracao/periodos/<uuid:academic_term_id>/editar/",
        views.academic_term_edit_view,
        name="academic_term_edit",
    ),
    # -- Ciclos lectivos (RF-INST-05, issue #16) --------------------------------
    path(
        "configuracao/ciclos-lectivos/",
        views.academic_cycle_list_view,
        name="academic_cycle_list",
    ),
    path(
        "configuracao/ciclos-lectivos/novo/",
        views.academic_cycle_create_view,
        name="academic_cycle_create",
    ),
    path(
        "configuracao/ciclos-lectivos/<uuid:academic_cycle_id>/editar/",
        views.academic_cycle_edit_view,
        name="academic_cycle_edit",
    ),
    # -- Feriados e dias não lectivos (RF-INST-07, issue #20) -------------------
    path(
        "configuracao/feriados/",
        views.non_teaching_day_list_view,
        name="non_teaching_day_list",
    ),
    path(
        "configuracao/feriados/novo/",
        views.non_teaching_day_create_view,
        name="non_teaching_day_create",
    ),
    path(
        "configuracao/feriados/<uuid:non_teaching_day_id>/editar/",
        views.non_teaching_day_edit_view,
        name="non_teaching_day_edit",
    ),
    # -- Cópias de segurança (RF-INST-*, issue #166) ----------------------------
    path("configuracao/backups/", views.backup_list_view, name="backup_list"),
    path(
        "configuracao/backups/<str:filename>/",
        views.backup_download_view,
        name="backup_download",
    ),
    # -- Configuração da fórmula de média (RF-INST-06, issue #18) --------------
    path(
        "avaliacao/formula/",
        views.grading_formula_config_view,
        name="grading_formula_config",
    ),
    path(
        "avaliacao/formula/curso/<uuid:course_id>/",
        views.course_grading_formula_view,
        name="course_grading_formula",
    ),
    path(
        "avaliacao/formula/disciplina/<uuid:subject_id>/",
        views.subject_grading_formula_view,
        name="subject_grading_formula",
    ),
]
