"""
Configuração de URLs raiz do projecto FenixSchool.

Cada app regista as suas próprias rotas em ``apps/<app>/urls.py`` e é incluída aqui
à medida que for sendo implementada (ver docs/10-stack-tecnologica-e-estrutura-projeto.md).
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("inscricoes/", include("apps.enrollment.urls")),
    path("admin-painel/", include("apps.admin_panel.urls")),
    path("encarregado/", include("apps.guardian_portal.urls")),
    path("notas/", include("apps.grading.urls")),
    path("presencas/", include("apps.attendance.urls")),
    path("", include("apps.public_site.urls")),
]
