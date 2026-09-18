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


def first_section_with_errors(default_form, sections) -> int:
    """For a stepped form (`templates/components/stepped_form.html`, or a
    hand-rolled multi-form wizard like `enrollment/student_inscription_form.html`)
    redisplayed after a failed submission: which step (1-indexed) the browser
    should open on, so a validation error on e.g. "Contactos" doesn't get
    silently hidden behind whichever step happened to be showing when the
    page reloads. Defaults to the first step when nothing points anywhere
    more specific (a first render with no errors yet, or a non-field error
    not tied to any particular section's fields).

    Each section may specify its own `"form"` (falling back to `default_form`
    when omitted) -- needed for a wizard spanning several distinct Django
    forms, not just one form's fields split across steps. A section with a
    `"fields"` list only counts an error there as belonging to that step;
    without one, any error anywhere in that section's form counts (used for
    a step that's really a whole separate form, e.g. "Encarregado de
    Educação" or "Consentimento").
    """
    for index, section in enumerate(sections, start=1):
        form = section.get("form", default_form)
        fields = section.get("fields")
        if fields is not None:
            if set(form.errors) & set(fields):
                return index
        elif form.errors:
            return index
    return 1
