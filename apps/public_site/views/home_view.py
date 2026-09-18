"""Página institucional pública (issue #100, RF-PUB-01, docs/06-modulos-e-
funcionalidades.md §6.3) -- acessível sem autenticação, tanto no Nó Central
como no Nó Local.
"""

from django.shortcuts import redirect, render

from apps.academic.models import Course

from ..services import get_the_institution


def home_view(request):
    institution = get_the_institution()
    if institution is None:
        # No institution yet -- this node hasn't been through the setup
        # wizard (issue #17), so there's nothing real to show at "/" yet.
        return redirect("core:setup_wizard")

    # `all_objects` (not `objects`): an anonymous, unauthenticated visitor
    # has no tenant context at all (`TenantMiddleware` only resolves one
    # from `request.user`), so `objects` would fail closed to an empty
    # queryset here -- `for_institution` filters explicitly instead,
    # exactly the "system code, not an ordinary user's request" case that
    # exemption is for (a public page showing this institution's own,
    # already-public course list).
    courses = (
        Course.all_objects.for_institution(institution.id)
        .select_related("department")
        .order_by("name")
    )

    return render(
        request,
        "public_site/home.html",
        {"institution": institution, "courses": courses},
    )
