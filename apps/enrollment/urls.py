"""Rotas da app `enrollment`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    # -- Inscrição (issue #45) -- "Inscrições → Alunos → Novo Aluno" ----------
    path("alunos/novo/", views.student_inscription_view, name="student_inscription"),
]
