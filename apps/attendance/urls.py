"""Rotas da app `attendance`."""

from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("lancar/", views.attendance_grid_selection_view, name="attendance_grid_selection"),
    path("lancar/grelha/", views.attendance_grid_view, name="attendance_grid"),
]
