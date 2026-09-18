"""Âmbito de acesso por perfil de utilizador na app `guardian_portal`."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Profile


def guardian_required(view_func):
    """Restricts a view to authenticated Encarregado de Educação users
    (issue #52) -- distinct from gating by the coarser
    `enrollment.view_student` Django permission (issue #29), which several
    staff profiles also hold for their own, unrelated admin-side visibility
    into student records.
    """

    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.profile != Profile.GUARDIAN:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view
