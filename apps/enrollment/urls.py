"""Rotas da app `enrollment`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("", views.index_view, name="index"),
    # -- Inscrição (issue #45) -- "Inscrições → Alunos → Novo Aluno" ----------
    path("alunos/novo/", views.student_inscription_view, name="student_inscription"),
    # -- Matrícula (issue #47) -- "Inscrições → Matrículas → Nova Matrícula" --
    path("matriculas/", views.student_search_view, name="student_search"),
    path(
        "matriculas/<uuid:student_id>/nova/",
        views.enrollment_create_view,
        name="enrollment_create",
    ),
]
