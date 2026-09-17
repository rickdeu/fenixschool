"""Rotas da app `core`.

Incluído em `config.urls` (ou num app agregador) quando a app tiver views implementadas.
"""

from django.urls import path

from .views import SetupWizardView

app_name = "core"

urlpatterns = [
    path("setup/", SetupWizardView.as_view(), name="setup_wizard"),
]
