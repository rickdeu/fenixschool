"""Shared helpers for institution-scoped views across apps."""

from django.contrib import messages
from django.shortcuts import redirect


def require_institution_context(request):
    """A Super Administrator has no `institution` of their own (`request.institution`
    is only set once they explicitly pick one to view -- see
    `apps.core.middleware.TenantMiddleware`, and that picker isn't built yet).
    Any institution-scoped view must call this first and return its redirect
    (if any) instead of crashing on a missing `institution` -- e.g. a
    `NOT NULL` constraint violation trying to save a record with no
    institution, rather than assuming, like most other institution-scoped
    views in this codebase, that it's always set.
    """
    if request.institution is None:
        messages.error(
            request,
            "Esta página está associada a uma instituição específica -- "
            "nenhuma instituição está seleccionada.",
        )
        return redirect("accounts:landing_placeholder")
    return None
