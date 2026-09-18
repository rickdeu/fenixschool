"""Edição/remoção de dia não lectivo (issue #20, RF-INST-07)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.forms import NonTeachingDayForm
from apps.core.models import NonTeachingDay
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.change_nonteachingday", raise_exception=True)
def non_teaching_day_edit_view(request, non_teaching_day_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    non_teaching_day = get_object_or_404(
        NonTeachingDay, pk=non_teaching_day_id, institution=request.institution
    )

    if request.method == "POST" and "delete" in request.POST:
        if not request.user.has_perm("core.delete_nonteachingday"):
            raise PermissionDenied
        description = non_teaching_day.description
        non_teaching_day.delete()
        success(request, f'"{description}" removido do calendário.')
        return redirect("admin_panel:non_teaching_day_list")

    if request.method == "POST":
        form = NonTeachingDayForm(request.POST, instance=non_teaching_day)
        if form.is_valid():
            form.save()
            success(request, f'"{non_teaching_day.description}" actualizado.')
            return redirect("admin_panel:non_teaching_day_list")
    else:
        form = NonTeachingDayForm(instance=non_teaching_day)

    return render(
        request,
        "admin_panel/non_teaching_day_form.html",
        {"form": form, "is_create": False, "non_teaching_day": non_teaching_day},
    )
