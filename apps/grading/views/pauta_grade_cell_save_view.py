"""Endpoint HTMX que grava a correcção de uma nota a partir do ecrã de
Pautas (issue #60) sem recarregar a página -- devolve apenas o fragmento
dessa célula, com feedback de sucesso/erro. Ao contrário de
`grade_cell_save_view` (issue #59), não exige que quem edita seja o
docente agendado: é uma correcção administrativa antes de homologar."""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from ..models import Grade, GradeReportClosedError
from ..services import NotaForaDaEscalaError, atualizar_nota_pauta


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def pauta_grade_cell_save_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.user.institution
    grade = get_object_or_404(Grade, pk=request.POST.get("grade_id"), institution=institution)
    raw_value = (request.POST.get("value") or "").strip()

    context = {"grade": grade, "value": raw_value, "closed": grade.is_grade_report_closed}

    if not raw_value:
        context["error"] = "Indique uma classificação."
        return render(request, "grading/_pauta_grade_row.html", context)

    try:
        atualizar_nota_pauta(grade=grade, value=raw_value)
    except NotaForaDaEscalaError as error:
        context["error"] = str(error)
    except GradeReportClosedError:
        context["error"] = "Esta pauta já está fechada -- a edição requer autorização."
        context["closed"] = True
    else:
        context["value"] = grade.value
        context["success"] = True
        context["closed"] = grade.is_grade_report_closed

    return render(request, "grading/_pauta_grade_row.html", context)
