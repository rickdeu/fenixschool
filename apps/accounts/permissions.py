"""Âmbito de acesso por perfil de utilizador na app `accounts`."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def require_profile(*profiles):
    """Returns a decorator restricting a view to users whose `profile` is
    one of `profiles` -- the shared shape behind every app-specific
    "<perfil>_required" decorator (`grading.permissions.docente_required`,
    `guardian_portal.permissions.guardian_required`, ...), instead of each
    reimplementing it.

    `user.is_superuser` always bypasses this check: "Super Administrador
    deve ter acesso a tudo, sem restrição alguma" -- the other half of that
    guarantee is `apps.accounts.services.ensure_super_admin_has_full_access`
    (which forces `is_superuser=True` for that profile, so every Django
    *permission* check already passes); this extends the same guarantee to
    views gated directly by `profile` instead of by a Django permission.
    Everything a Super Administrador can see through this bypass is still
    scoped to their own institution by the ordinary tenant machinery
    (`apps.core.middleware.TenantMiddleware`/`TenantManager`) -- this only
    ever relaxes *which profile* may open the view, never *which
    institution*'s data it returns.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_superuser and request.user.profile not in profiles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
