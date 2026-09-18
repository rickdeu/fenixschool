"""Criação de dia não lectivo (issue #20, RF-INST-07)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.core.forms import NonTeachingDayForm
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.add_nonteachingday", raise_exception=True)
def non_teaching_day_create_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = NonTeachingDayForm(request.POST)
        if form.is_valid():
            non_teaching_day = form.save(commit=False)
            non_teaching_day.institution = request.institution
            non_teaching_day.origin_node_id = get_current_node_id()
            non_teaching_day.save()
            success(request, f'"{non_teaching_day.description}" adicionado ao calendário.')
            return redirect("admin_panel:non_teaching_day_list")
    else:
        form = NonTeachingDayForm()

    return render(
        request, "admin_panel/non_teaching_day_form.html", {"form": form, "is_create": True}
    )
