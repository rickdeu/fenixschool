"""Rotas da app `guardian_portal`."""

from django.urls import path

from . import views

app_name = "guardian_portal"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
]
