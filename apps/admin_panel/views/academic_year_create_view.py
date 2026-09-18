"""Criação de ano lectivo (issue #16, RF-INST-03)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.core.forms import AcademicYearForm
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.add_academicyear", raise_exception=True)
def academic_year_create_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            year = form.save(commit=False)
            year.institution = request.institution
            year.origin_node_id = get_current_node_id()
            try:
                year.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success(request, f'"{year.designation}" adicionado.')
                return redirect("admin_panel:academic_year_list")
    else:
        form = AcademicYearForm()

    return render(request, "admin_panel/academic_year_form.html", {"form": form, "is_create": True})
