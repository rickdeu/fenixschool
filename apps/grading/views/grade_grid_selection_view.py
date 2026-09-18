"""Selecção de turma/disciplina/tipo de avaliação/período antes da grelha
de lançamento de notas (issue #59)."""

from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import GradeGridSelectionForm
from ..permissions import docente_required


@docente_required
def grade_grid_selection_view(request):
    form = GradeGridSelectionForm(
        request.POST or None, teacher=request.user, institution=request.user.institution
    )
    if request.method == "POST" and form.is_valid():
        assignment = form.assignments_by_key[form.cleaned_data["assignment"]]
        query = urlencode(
            {
                "turma": assignment.school_class_id,
                "disciplina": assignment.subject_id,
                "tipo": form.cleaned_data["evaluation_type"].id,
                "periodo": form.cleaned_data["academic_term"].id,
            }
        )
        return redirect(f"{reverse('grading:grade_grid')}?{query}")

    return render(request, "grading/grade_grid_selection.html", {"form": form})
