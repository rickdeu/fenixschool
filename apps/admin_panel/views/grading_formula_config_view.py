"""View de configuração da fórmula de média por omissão da instituição
(RF-INST-06, issue #18)."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.core.view_helpers import require_institution_context
from apps.grading.services import (
    calculate_average,
    ensure_default_evaluation_types,
    set_institution_default_formula,
)

from ..forms import GradingFormulaForm

# Exemplo ilustrativo (não são classificações reais de nenhum aluno) usado
# apenas para demonstrar, com a fórmula actualmente introduzida, como
# `apps.grading.services.calculate_average` combina os pesos -- RF-INST-06's
# "pré-visualização do cálculo".
SAMPLE_GRADE_VALUES = [Decimal("14"), Decimal("16"), Decimal("12"), Decimal("18"), Decimal("10")]


def _build_preview(formula, evaluation_types):
    if not formula:
        return None
    sample_grades = {
        evaluation_type.name: SAMPLE_GRADE_VALUES[index % len(SAMPLE_GRADE_VALUES)]
        for index, evaluation_type in enumerate(evaluation_types)
        if evaluation_type.name in formula
    }
    return {"grades": sample_grades, "average": calculate_average(sample_grades, formula)}


@login_required
@permission_required("core.change_institution", raise_exception=True)
def grading_formula_config_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    evaluation_types = ensure_default_evaluation_types(
        institution, origin_node_id=get_current_node_id()
    )
    saved_formula = {
        name: Decimal(str(weight)) for name, weight in institution.default_grading_formula.items()
    }
    # Falls back to each EvaluationType's own suggested `default_weight` only
    # for a first-run institution that hasn't saved a formula yet -- once one
    # is saved, `saved_formula` (however it was set) is always shown as-is.
    initial_formula = saved_formula or {
        evaluation_type.name: evaluation_type.default_weight
        for evaluation_type in evaluation_types
    }

    if request.method == "POST":
        form = GradingFormulaForm(request.POST, institution=institution)
        if form.is_valid():
            set_institution_default_formula(institution, form.formula)
            messages.success(request, "Fórmula de média por omissão actualizada.")
            return redirect("admin_panel:grading_formula_config")
    else:
        form = GradingFormulaForm(institution=institution, initial_formula=initial_formula)

    preview = _build_preview(
        getattr(form, "formula", initial_formula) or initial_formula, evaluation_types
    )

    return render(
        request,
        "admin_panel/grading_formula_form.html",
        {"form": form, "preview": preview, "scope_label": institution.name},
    )
