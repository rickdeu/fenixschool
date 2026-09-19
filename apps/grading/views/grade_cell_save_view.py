"""Endpoint HTMX que grava uma linha da grelha de lançamento de notas
(issue #59) sem recarregar a página -- devolve apenas o fragmento dessa
linha, com feedback de sucesso/erro."""

import uuid

from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from apps.academic.models import Subject
from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment

from ..models import EvaluationType, GradeReportClosedError
from ..permissions import docente_required
from ..services import DocenteNaoAssociadoError, NotaForaDaEscalaError, lancar_ou_atualizar_nota


@docente_required
def grade_cell_save_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.user.institution
    enrollment = get_object_or_404(
        Enrollment, pk=request.POST.get("enrollment"), institution=institution
    )
    subject = get_object_or_404(Subject, pk=request.POST.get("subject"), institution=institution)
    evaluation_type = get_object_or_404(
        EvaluationType, pk=request.POST.get("evaluation_type"), institution=institution
    )
    academic_term = get_object_or_404(
        AcademicTerm, pk=request.POST.get("academic_term"), institution=institution
    )
    raw_value = (request.POST.get("value") or "").strip()

    context = {
        "enrollment": enrollment,
        "subject": subject,
        "evaluation_type": evaluation_type,
        "academic_term": academic_term,
        "value": raw_value,
    }

    if not raw_value:
        context["error"] = "Indique uma classificação."
        return render(request, "grading/_grade_row.html", context)

    try:
        grade = lancar_ou_atualizar_nota(
            teacher=request.user,
            enrollment=enrollment,
            subject=subject,
            evaluation_type=evaluation_type,
            academic_term=academic_term,
            value=raw_value,
            origin_node_id=uuid.uuid4(),
        )
    except NotaForaDaEscalaError as error:
        context["error"] = str(error)
    except DocenteNaoAssociadoError:
        context["error"] = "Não está associado a esta disciplina/turma."
    except GradeReportClosedError:
        context["error"] = "Esta pauta já está fechada -- a edição requer autorização."
    else:
        context["value"] = grade.value
        context["success"] = True
        context["qualitative_level"] = grade.qualitative_level

    return render(request, "grading/_grade_row.html", context)
