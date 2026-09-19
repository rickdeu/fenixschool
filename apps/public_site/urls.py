"""Rotas da app `public_site`."""

from django.urls import path

from . import views

app_name = "public_site"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("calendario/", views.calendar_view, name="calendar"),
    path("candidatura/", views.pre_application_view, name="pre_application"),
    path(
        "candidatura/comprovativo/",
        views.application_receipt_view,
        name="application_receipt",
    ),
]
