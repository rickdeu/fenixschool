"""Lista de ciclos lectivos da instituição (issue #16, RF-INST-05)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.core.models import AcademicCycle
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.view_academiccycle", raise_exception=True)
def academic_cycle_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    cycles = AcademicCycle.objects.filter(institution=request.institution).order_by("order")

    return render(request, "admin_panel/academic_cycle_list.html", {"cycles": cycles})
