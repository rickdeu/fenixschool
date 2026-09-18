"""Lista de feriados/dias não lectivos da instituição (issue #20, RF-INST-07)."""

from datetime import date

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.core.models import NonTeachingDay
from apps.core.services import seed_national_holidays
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.view_nonteachingday", raise_exception=True)
def non_teaching_day_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    if request.method == "POST" and "seed_year" in request.POST:
        if not request.user.has_perm("core.add_nonteachingday"):
            raise PermissionDenied
        year = int(request.POST["seed_year"])
        created = seed_national_holidays(
            institution, origin_node_id=get_current_node_id(), year=year
        )
        if created:
            success(request, f"{created} feriado(s) nacional(is) de {year} pré-carregado(s).")
        else:
            success(request, f"Os feriados nacionais de {year} já estavam todos carregados.")
        return redirect("admin_panel:non_teaching_day_list")

    non_teaching_days = NonTeachingDay.objects.filter(institution=institution).order_by("date")
    current_year = date.today().year

    return render(
        request,
        "admin_panel/non_teaching_day_list.html",
        {
            "non_teaching_days": non_teaching_days,
            "seed_year_choices": [current_year, current_year + 1],
        },
    )
