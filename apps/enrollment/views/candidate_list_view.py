"""Lista de candidatos pendentes, com admissão para a Inscrição (issue #42,
RF-MAT-10) -- inclui os que chegaram pela pré-candidatura pública (issue #102)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.core.view_helpers import require_institution_context

from ..models import Candidate


@login_required
@permission_required("enrollment.view_candidate", raise_exception=True)
def candidate_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    candidates = Candidate.objects.filter(
        institution=institution, status=Candidate.Status.PENDING
    ).order_by("-application_date")

    return render(request, "enrollment/candidate_list.html", {"candidates": candidates})
