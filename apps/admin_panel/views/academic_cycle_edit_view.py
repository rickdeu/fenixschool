"""Edição/remoção de ciclo lectivo (issue #16, RF-INST-05)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.forms import AcademicCycleForm
from apps.core.models import AcademicCycle
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.change_academiccycle", raise_exception=True)
def academic_cycle_edit_view(request, academic_cycle_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    cycle = get_object_or_404(
        AcademicCycle, pk=academic_cycle_id, institution=request.institution
    )

    if request.method == "POST" and "delete" in request.POST:
        if not request.user.has_perm("core.delete_academiccycle"):
            raise PermissionDenied
        designation = cycle.designation
        cycle.delete()
        success(request, f'"{designation}" removido.')
        return redirect("admin_panel:academic_cycle_list")

    if request.method == "POST":
        form = AcademicCycleForm(request.POST, instance=cycle)
        if form.is_valid():
            try:
                form.instance.full_clean()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                form.save()
                success(request, f'"{cycle.designation}" actualizado.')
                return redirect("admin_panel:academic_cycle_list")
    else:
        form = AcademicCycleForm(instance=cycle)

    return render(
        request,
        "admin_panel/academic_cycle_form.html",
        {"form": form, "is_create": False, "cycle": cycle},
    )
