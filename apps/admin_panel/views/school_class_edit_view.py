"""Edição de turma (RF-CURR-05, issue #34) -- até agora só via Django Admin."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.forms import SchoolClassForm
from apps.academic.models import SchoolClass
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("academic.change_schoolclass", raise_exception=True)
def school_class_edit_view(request, school_class_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    school_class = get_object_or_404(
        SchoolClass, pk=school_class_id, institution=request.institution
    )

    if request.method == "POST" and "delete" in request.POST:
        if not request.user.has_perm("academic.delete_schoolclass"):
            raise PermissionDenied
        designation = school_class.designation
        try:
            school_class.delete()
        except ProtectedError:
            messages.error(
                request,
                f'"{designation}" não pode ser removida: já tem matrículas ou horários associados.',
            )
        else:
            messages.success(request, f'"{designation}" removida.')
        return redirect("admin_panel:school_class_list")

    if request.method == "POST":
        form = SchoolClassForm(request.POST, instance=school_class, institution=request.institution)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as validation_error:
                form.add_error(None, validation_error)
            else:
                messages.success(request, f'"{school_class.designation}" actualizada.')
                return redirect("admin_panel:school_class_list")
    else:
        form = SchoolClassForm(instance=school_class, institution=request.institution)

    return render(
        request,
        "admin_panel/school_class_form.html",
        {"form": form, "is_create": False, "school_class": school_class},
    )
