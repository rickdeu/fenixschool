"""Boletim de notas de um aluno, num trimestre (issue #97, RF-REL-04) --
extracto individual, por disciplina: as notas por tipo de avaliação e a
média final calculada (`FinalGrade`)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment

from ..services import get_boletim_rows


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def boletim_view(request):
    institution = request.user.institution
    enrollment = get_object_or_404(
        Enrollment, pk=request.GET.get("aluno"), institution=institution
    )
    academic_term = get_object_or_404(
        AcademicTerm, pk=request.GET.get("periodo"), institution=institution
    )

    rows = get_boletim_rows(
        institution=institution, enrollment=enrollment, academic_term=academic_term
    )

    return render(
        request,
        "grading/boletim.html",
        {
            "enrollment": enrollment,
            "academic_term": academic_term,
            "rows": rows,
        },
    )
