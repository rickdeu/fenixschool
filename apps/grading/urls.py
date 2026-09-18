"""Rotas da app `grading`."""

from django.urls import path

from . import views

app_name = "grading"

urlpatterns = [
    path("lancar/", views.grade_grid_selection_view, name="grade_grid_selection"),
    path("lancar/grelha/", views.grade_grid_view, name="grade_grid"),
    path("lancar/grelha/gravar/", views.grade_cell_save_view, name="grade_cell_save"),
    path("pautas/", views.pauta_management_view, name="pauta_management"),
    path("pautas/ver/", views.pauta_detail_view, name="pauta_detail"),
    path("pautas/nota/gravar/", views.pauta_grade_cell_save_view, name="pauta_grade_cell_save"),
    path("situacao-final/", views.final_situation_view, name="final_situation"),
]
