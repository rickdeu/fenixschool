"""View de sobreposição da fórmula de média ao nível do Curso (RF-INST-06,
issue #18)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import Course
from apps.core.context import get_current_node_id
from apps.grading.services import (
    ensure_default_evaluation_types,
    resolve_grading_formula,
    set_course_formula_override,
)

from ..forms import GradingFormulaForm
from .grading_formula_config_view import _build_preview


@login_required
@permission_required("academic.change_course", raise_exception=True)
def course_grading_formula_view(request, course_id):
    institution = request.institution
    course = get_object_or_404(Course, pk=course_id, institution=institution)
    evaluation_types = ensure_default_evaluation_types(
        institution, origin_node_id=get_current_node_id()
    )
    initial_formula = resolve_grading_formula(institution=institution, course=course)

    if request.method == "POST":
        if "clear" in request.POST:
            set_course_formula_override(course, None, origin_node_id=get_current_node_id())
            messages.success(request, f'Sobreposição do curso "{course}" removida.')
            return redirect("admin_panel:course_grading_formula", course_id=course.id)

        form = GradingFormulaForm(request.POST, institution=institution)
        if form.is_valid():
            set_course_formula_override(
                course, form.formula, origin_node_id=get_current_node_id()
            )
            messages.success(request, f'Sobreposição do curso "{course}" actualizada.')
            return redirect("admin_panel:course_grading_formula", course_id=course.id)
    else:
        form = GradingFormulaForm(institution=institution, initial_formula=initial_formula)

    preview = _build_preview(
        getattr(form, "formula", initial_formula) or initial_formula, evaluation_types
    )

    return render(
        request,
        "admin_panel/grading_formula_form.html",
        {
            "form": form,
            "preview": preview,
            "scope_label": f'Curso "{course}"',
            "can_clear": True,
        },
    )
