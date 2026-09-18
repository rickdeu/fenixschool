"""Rotas da app `public_site`."""

from django.urls import path

from . import views

app_name = "public_site"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("calendario/", views.calendar_view, name="calendar"),
]
