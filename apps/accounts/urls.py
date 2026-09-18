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
    # -- 2FA (issue #25) ---------------------------------------------------------
    path("2fa/configurar/", views.two_factor_setup_view, name="two_factor_setup"),
    path("2fa/verificar/", views.two_factor_verify_view, name="two_factor_verify"),
    # -- Preferências ----------------------------------------------------------
    path(
        "idioma/",
        views.set_preferred_language_view,
        name="set_preferred_language",
    ),
    # -- Área do utilizador ----------------------------------------------------
    # Not "" / the bare root: that belongs to the public site's own homepage
    # (apps.public_site, issue #100), not to this post-login placeholder.
    path("inicio/", views.landing_placeholder, name="landing_placeholder"),
]
