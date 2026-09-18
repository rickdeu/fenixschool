"""Lista de anos lectivos e respectivos períodos (issue #16, RF-INST-03/04)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import error, success
from django.shortcuts import redirect, render

from apps.core.models import AcademicYear
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.view_academicyear", raise_exception=True)
def academic_year_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    if request.method == "POST" and "mark_current" in request.POST:
        if not request.user.has_perm("core.change_academicyear"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        year = AcademicYear.objects.filter(
            institution=institution, pk=request.POST["mark_current"]
        ).first()
        if year is None:
            error(request, "Ano lectivo não encontrado.")
        else:
            AcademicYear.objects.filter(institution=institution, is_current=True).update(
                is_current=False
            )
            year.is_current = True
            year.save(update_fields=["is_current"])
            success(request, f'"{year.designation}" marcado como o ano lectivo corrente.')
        return redirect("admin_panel:academic_year_list")

    years = AcademicYear.objects.filter(institution=institution).prefetch_related("terms")

    return render(request, "admin_panel/academic_year_list.html", {"years": years})
