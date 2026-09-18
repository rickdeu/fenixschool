"""Criação de período lectivo dentro de um ano lectivo (issue #16, RF-INST-04)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.context import get_current_node_id
from apps.core.forms import AcademicTermForm
from apps.core.models import AcademicYear
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.add_academicterm", raise_exception=True)
def academic_term_create_view(request, academic_year_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    year = get_object_or_404(AcademicYear, pk=academic_year_id, institution=request.institution)

    if request.method == "POST":
        form = AcademicTermForm(request.POST)
        if form.is_valid():
            term = form.save(commit=False)
            term.institution = request.institution
            term.academic_year = year
            term.origin_node_id = get_current_node_id()
            try:
                term.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success(request, f'Trimestre {term.number} adicionado a "{year.designation}".')
                return redirect("admin_panel:academic_year_list")
    else:
        form = AcademicTermForm()

    return render(
        request,
        "admin_panel/academic_term_form.html",
        {"form": form, "is_create": True, "year": year},
    )
