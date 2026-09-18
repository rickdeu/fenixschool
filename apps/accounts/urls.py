"""Rotas da app `accounts`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # -- Autenticação --------------------------------------------------------
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    # -- Área do utilizador ----------------------------------------------------
    # Not "" / the bare root: that belongs to the public site's own homepage
    # (apps.public_site, issue #100), not to this post-login placeholder.
    path("inicio/", views.landing_placeholder, name="landing_placeholder"),
]
