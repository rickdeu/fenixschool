"""Calendário escolar público (issue #104, docs/06-modulos-e-
funcionalidades.md §6.3) -- acessível sem autenticação.
"""

from django.shortcuts import redirect, render

from apps.core.models import AcademicTerm, AcademicYear, NonTeachingDay

from ..services import get_the_institution


def calendar_view(request):
    institution = get_the_institution()
    if institution is None:
        return redirect("core:setup_wizard")

    # `all_objects` (not `objects`): same reasoning as `home_view` -- an
    # anonymous visitor has no tenant context to filter by, so this is the
    # deliberate, explicit "system code showing this institution's own
    # already-public data" exemption, not an ordinary user's request.
    academic_year = (
        AcademicYear.all_objects.for_institution(institution.id).filter(is_current=True).first()
    )

    terms = []
    non_teaching_days = NonTeachingDay.all_objects.for_institution(institution.id).order_by("date")
    if academic_year is not None:
        # `all_objects` here too -- `academic_year.terms` (the related
        # manager) would go through `AcademicTerm.objects` (the same
        # tenant-context-dependent `TenantManager`), empty for the same
        # reason as above.
        terms = list(
            AcademicTerm.all_objects.filter(academic_year=academic_year).order_by("number")
        )
        non_teaching_days = non_teaching_days.filter(
            date__gte=academic_year.start_date, date__lte=academic_year.end_date
        )

    return render(
        request,
        "public_site/calendar.html",
        {
            "academic_year": academic_year,
            "terms": terms,
            "non_teaching_days": non_teaching_days,
        },
    )
