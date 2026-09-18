"""View de login (issue #24)."""

from django.contrib.auth import views as auth_views
from django.urls import reverse

from ..forms import LoginForm
from ..services import get_login_redirect_url_name


class LoginView(auth_views.LoginView):
    """Login by email/phone, no institution selector (issue #24).

    Doesn't redirect straight to `get_login_redirect_url_name()`'s
    destination for profiles that require 2FA (issue #25) -- that's not
    this view's concern at all: `RequireTwoFactorMiddleware` intercepts the
    very next request and redirects to the 2FA setup/verify flow instead,
    which redirects here again once completed.
    """

    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse(get_login_redirect_url_name(self.request.user))
