"""Signals da app `accounts`."""

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User
from .services import register_failed_login, reset_lockout_state, sync_profile_group_membership


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


@receiver(post_save, sender=User)
def sync_group_on_profile_change(sender, instance, **kwargs):
    """issue #113: `user.groups` (and therefore every permission check)
    always reflects `user.profile`, on every creation/edit, regardless of
    which code path (this app's own forms, Django Admin, a management
    command, `createsuperuser`) touched it."""
    sync_profile_group_membership(instance)
