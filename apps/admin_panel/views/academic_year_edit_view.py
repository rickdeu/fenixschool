"""Edição/remoção de ano lectivo (issue #16, RF-INST-03)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.forms import AcademicYearForm
from apps.core.models import AcademicYear
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.change_academicyear", raise_exception=True)
def academic_year_edit_view(request, academic_year_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    year = get_object_or_404(AcademicYear, pk=academic_year_id, institution=request.institution)

    if request.method == "POST" and "delete" in request.POST:
        if not request.user.has_perm("core.delete_academicyear"):
            raise PermissionDenied
        designation = year.designation
        year.delete()
        success(request, f'"{designation}" removido.')
        return redirect("admin_panel:academic_year_list")

    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=year)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success(request, f'"{year.designation}" actualizado.')
                return redirect("admin_panel:academic_year_list")
    else:
        form = AcademicYearForm(instance=year)

    return render(
        request,
        "admin_panel/academic_year_form.html",
        {"form": form, "is_create": False, "year": year},
    )
