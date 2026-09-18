"""View de login (issue #24)."""

from django.contrib.auth import views as auth_views
from django.urls import reverse

from ..forms import LoginForm
from ..models import Profile

# Where each profile lands right after login (issue #24's "redireciona ao
# dashboard correcto consoante o perfil"). Profiles whose own portal/dashboard
# doesn't exist yet (issues #105, #109, #119, ...) land on the placeholder
# below instead of a fabricated one -- add/replace entries here as each
# lands, rather than this view guessing at URLs that don't exist yet.
PROFILE_LANDING_URL_NAMES = {
    Profile.SUPER_ADMIN: "admin:index",
    Profile.INSTITUTION_ADMIN: "admin:index",
    Profile.PEDAGOGICAL_DIRECTION: "admin:index",
    Profile.SECRETARY: "admin:index",
    Profile.FINANCE: "admin:index",
    Profile.HR: "admin:index",
}


class LoginView(auth_views.LoginView):
    """Login by email/phone, no institution selector (issue #24)."""

    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        url_name = PROFILE_LANDING_URL_NAMES.get(
            self.request.user.profile, "accounts:landing_placeholder"
        )
        return reverse(url_name)
