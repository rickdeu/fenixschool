"""Exportação do Boletim em PDF oficial (issue #97, RF-REL-04) -- reaproveita
a mesma selecção aluno/trimestre e as mesmas linhas que `boletim_view` já
mostra no ecrã, delegando a numeração/auditoria/renderização a
`apps.reports.services.gerar_boletim_pdf`."""

import uuid

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment
from apps.reports.services import gerar_boletim_pdf

from ..services import get_boletim_rows


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def boletim_pdf_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.user.institution
    enrollment = get_object_or_404(
        Enrollment, pk=request.POST.get("aluno"), institution=institution
    )
    academic_term = get_object_or_404(
        AcademicTerm, pk=request.POST.get("periodo"), institution=institution
    )

    rows = get_boletim_rows(
        institution=institution, enrollment=enrollment, academic_term=academic_term
    )

    issued, pdf = gerar_boletim_pdf(
        enrollment=enrollment,
        academic_term=academic_term,
        rows=rows,
        issued_by=request.user,
        origin_node_id=uuid.uuid4(),
    )

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = issued.formatted_number.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response
