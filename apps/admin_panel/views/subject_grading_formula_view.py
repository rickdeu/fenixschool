"""View de sobreposição da fórmula de média ao nível da Disciplina (RF-INST-06,
issue #18)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import Subject
from apps.core.context import get_current_node_id
from apps.grading.services import (
    ensure_default_evaluation_types,
    resolve_grading_formula,
    set_subject_formula_override,
)

from ..forms import GradingFormulaForm
from .grading_formula_config_view import _build_preview, require_institution_context


@login_required
@permission_required("academic.change_subject", raise_exception=True)
def subject_grading_formula_view(request, subject_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    subject = get_object_or_404(Subject, pk=subject_id, institution=institution)
    evaluation_types = ensure_default_evaluation_types(
        institution, origin_node_id=get_current_node_id()
    )
    initial_formula = resolve_grading_formula(
        institution=institution, course=subject.course, subject=subject
    )

    if request.method == "POST":
        if "clear" in request.POST:
            set_subject_formula_override(subject, None, origin_node_id=get_current_node_id())
            messages.success(request, f'Sobreposição da disciplina "{subject}" removida.')
            return redirect("admin_panel:subject_grading_formula", subject_id=subject.id)

        form = GradingFormulaForm(request.POST, institution=institution)
        if form.is_valid():
            set_subject_formula_override(
                subject, form.formula, origin_node_id=get_current_node_id()
            )
            messages.success(request, f'Sobreposição da disciplina "{subject}" actualizada.')
            return redirect("admin_panel:subject_grading_formula", subject_id=subject.id)
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
            "scope_label": f'Disciplina "{subject}"',
            "can_clear": True,
        },
    )
