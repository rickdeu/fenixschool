"""Edição/remoção de período lectivo (issue #16, RF-INST-04)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.forms import AcademicTermForm
from apps.core.models import AcademicTerm
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.change_academicterm", raise_exception=True)
def academic_term_edit_view(request, academic_term_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    term = get_object_or_404(
        AcademicTerm, pk=academic_term_id, institution=request.institution
    )

    if request.method == "POST" and "delete" in request.POST:
        if not request.user.has_perm("core.delete_academicterm"):
            raise PermissionDenied
        number = term.number
        year = term.academic_year
        term.delete()
        success(request, f'Período {number} de "{year.designation}" removido.')
        return redirect("admin_panel:academic_year_list")

    if request.method == "POST":
        form = AcademicTermForm(request.POST, instance=term)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success(request, f'Período {term.number} actualizado.')
                return redirect("admin_panel:academic_year_list")
    else:
        form = AcademicTermForm(instance=term)

    return render(
        request,
        "admin_panel/academic_term_form.html",
        {"form": form, "is_create": False, "term": term, "year": term.academic_year},
    )
