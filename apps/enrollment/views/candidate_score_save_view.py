"""Endpoint HTMX que grava a nota da prova de aptidão de um Candidato
(feedback do utilizador: "ao inserir as notas a gravação também deve ser
automática desde o momento que a nota é inserida") sem recarregar a
página -- mesmo padrão de `grading.grade_cell_save_view`/
`pauta_grade_cell_save_view`.

Devolve três fragmentos: a própria célula da nota (alvo directo do
pedido) e, via `hx-swap-oob`, a célula de Estado e a célula de Acção --
ambas dependem da nota que acabou de ser gravada, por isso têm de mudar
na mesma resposta, não só depois de recarregar a página."""

from decimal import InvalidOperation

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from ..models import Candidate
from ..services import (
    CandidateAlreadyDecidedError,
    ExamScoreOutOfRangeError,
    registar_nota_candidato,
)


@login_required
@permission_required("enrollment.view_candidate", raise_exception=True)
def candidate_score_save_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.institution
    candidate = get_object_or_404(
        Candidate, pk=request.POST.get("candidate_id"), institution=institution
    )
    raw_value = (request.POST.get("score") or "").strip()

    context = {"candidate": candidate}
    if not raw_value:
        context["error"] = "Indique uma nota."
    else:
        try:
            registar_nota_candidato(candidate=candidate, score=raw_value)
        except (InvalidOperation, TypeError):
            context["error"] = "Indique uma nota válida (0-20)."
        except ExamScoreOutOfRangeError as error:
            context["error"] = str(error)
        except CandidateAlreadyDecidedError as error:
            context["error"] = str(error)
        else:
            context["success"] = True

    return render(request, "enrollment/_candidate_row_status.html", context)
