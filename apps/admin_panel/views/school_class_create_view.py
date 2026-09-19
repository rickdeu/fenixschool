"""Criação de turma (RF-CURR-05, issue #34) -- até agora só via Django Admin."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from apps.academic.forms import SchoolClassForm
from apps.core.context import get_current_node_id
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("academic.add_schoolclass", raise_exception=True)
def school_class_create_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    if request.method == "POST":
        form = SchoolClassForm(request.POST, institution=institution)
        if form.is_valid():
            school_class = form.save(commit=False)
            school_class.institution = institution
            school_class.origin_node_id = get_current_node_id()
            try:
                school_class.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                success(request, f'"{school_class.designation}" criada.')
                return redirect("admin_panel:school_class_list")
    else:
        form = SchoolClassForm(institution=institution)

    return render(request, "admin_panel/school_class_form.html", {"form": form, "is_create": True})
