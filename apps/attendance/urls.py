"""Rotas da app `attendance`."""

from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("lancar/", views.attendance_grid_selection_view, name="attendance_grid_selection"),
    path("lancar/grelha/", views.attendance_grid_view, name="attendance_grid"),
    path("faltas/", views.absence_list_view, name="absence_list"),
    path(
        "faltas/<uuid:attendance_id>/justificar/",
        views.justify_absence_view,
        name="justify_absence",
    ),
    path(
        "faltas/<uuid:attendance_id>/anexo/",
        views.justification_attachment_view,
        name="justification_attachment",
    ),
    path("mapa/", views.attendance_map_view, name="attendance_map"),
    path("mapa/docente/", views.docente_attendance_map_view, name="docente_attendance_map"),
]
