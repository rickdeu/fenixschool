"""View de logout (issue #24)."""

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("accounts:login")
