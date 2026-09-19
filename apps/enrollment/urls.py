"""Rotas da app `enrollment`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("", views.index_view, name="index"),
    # -- Candidatos (issue #42/#102) -- admissão para a Inscrição -------------
    path("candidatos/", views.candidate_list_view, name="candidate_list"),
    path("candidatos/nota/gravar/", views.candidate_score_save_view, name="candidate_score_save"),
    # -- Inscrição (issue #45) -- "Inscrições → Alunos → Novo Aluno" ----------
    path("alunos/novo/", views.student_inscription_view, name="student_inscription"),
    # -- Matrícula (issue #47) -- "Inscrições → Matrículas → Nova Matrícula" --
    path("matriculas/", views.student_search_view, name="student_search"),
    path(
        "matriculas/<uuid:student_id>/nova/",
        views.enrollment_create_view,
        name="enrollment_create",
    ),
    # -- Histórico/transferência/anulação (issues #49/#50/#51) -----------------
    path("alunos/<uuid:student_id>/", views.student_detail_view, name="student_detail"),
    # -- Matrícula em lote (issue #241) -- admitidos por candidatura -----------
    path("matriculas/lote/", views.bulk_enrollment_view, name="bulk_enrollment"),
    # -- Declarações (issue #94, RF-REL-01) ------------------------------------
    path("declaracoes/", views.declaracao_selection_view, name="declaracao_selection"),
    path("declaracoes/pdf/", views.declaracao_pdf_view, name="declaracao_pdf"),
]
