"""Signals da app `accounts`."""

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models import Q
from django.dispatch import receiver

from .models import User
from .services import register_failed_login, reset_lockout_state


@receiver(user_login_failed)
def lock_out_after_repeated_failures(sender, credentials, **kwargs):
    """Progressive account lockout after repeated failed logins (issue #26,
    RNF-SEC-02) -- fired once by `django.contrib.auth.authenticate()`
    whenever every configured backend rejects the attempt, regardless of
    which one (or which login screen: `accounts:login` or the Django
    Admin's own) it came through.
    """
    username = credentials.get("username")
    if not username:
        return

    user = User.objects.filter(
        Q(email__iexact=username) | Q(phone=username) | Q(username=username)
    ).first()
    if user is not None:
        register_failed_login(user)


@receiver(user_logged_in)
def reset_lockout_on_successful_login(sender, user, **kwargs):
    reset_lockout_state(user)
