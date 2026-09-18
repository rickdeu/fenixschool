"""Criação de ciclo lectivo (issue #16, RF-INST-05)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.core.forms import AcademicCycleForm
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.add_academiccycle", raise_exception=True)
def academic_cycle_create_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = AcademicCycleForm(request.POST)
        if form.is_valid():
            cycle = form.save(commit=False)
            cycle.institution = request.institution
            cycle.origin_node_id = get_current_node_id()
            try:
                cycle.full_clean()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                cycle.save()
                success(request, f'"{cycle.designation}" adicionado.')
                return redirect("admin_panel:academic_cycle_list")
    else:
        form = AcademicCycleForm()

    return render(
        request, "admin_panel/academic_cycle_form.html", {"form": form, "is_create": True}
    )
