"""Authentication backends for `accounts` -- issue #24, docs/09-seguranca-e-
privacidade.md §9.2: "Login por email ou telefone + password (nunca por
selecção manual de instituição)".
"""

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class AccountLockoutMixin:
    """Denies authentication outright for an account currently locked out
    (issue #26, RNF-SEC-02) -- checked *before* trusting a correct
    password, so a locked account can never authenticate (right password or
    not) until the lockout expires or an Administrator unlocks it manually.
    """

    def user_can_authenticate(self, user):
        if user.is_locked:
            return False
        return super().user_can_authenticate(user)


class EmailOrPhoneBackend(AccountLockoutMixin, ModelBackend):
    """Authenticates by `email` or `phone` instead of `username`.

    Kept alongside `LockoutAwareModelBackend` (see
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


class LockoutAwareModelBackend(AccountLockoutMixin, ModelBackend):
    """Identical to Django's own `ModelBackend` (username-based -- used by
    the Django Admin's own login screen), but also enforces the account
    lockout (issue #26). A separate class, not just `ModelBackend` directly
    in `AUTHENTICATION_BACKENDS`, so an admin login can't bypass the same
    lockout enforced everywhere else.
    """
