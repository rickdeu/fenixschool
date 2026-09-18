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
