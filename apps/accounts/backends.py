"""Authentication backends for `accounts` -- issue #24, docs/09-seguranca-e-
privacidade.md §9.2: "Login por email ou telefone + password (nunca por
selecção manual de instituição)".
"""

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrPhoneBackend(ModelBackend):
    """Authenticates by `email` or `phone` instead of `username`.

    Kept alongside the default `ModelBackend` (see
    `AUTHENTICATION_BACKENDS`, config/settings/base.py) rather than
    replacing it, so username-based logins (the Django Admin's own login
    screen, `createsuperuser`-created accounts) keep working unaffected --
    this backend only ever matches by `email`/`phone`.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(Q(email__iexact=username) | Q(phone=username))
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
