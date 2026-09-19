"""Emissão de uma Declaração em PDF (issue #94, RF-REL-01) -- delega a
validação/numeração/auditoria/renderização a
`apps.enrollment.services.emitir_declaracao`."""

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect

from ..models import Enrollment
from ..services import TipoDeDeclaracaoIncompativelError, emitir_declaracao


@login_required
@permission_required("reports.add_issueddocument", raise_exception=True)
def declaracao_pdf_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.user.institution
    enrollment = get_object_or_404(
        Enrollment, pk=request.POST.get("matricula"), institution=institution
    )
    declaracao_type = request.POST.get("tipo")

    try:
        issued, pdf = emitir_declaracao(
            enrollment=enrollment,
            declaracao_type=declaracao_type,
            issued_by=request.user,
            origin_node_id=uuid.uuid4(),
        )
    except TipoDeDeclaracaoIncompativelError as error:
        messages.error(request, str(error))
        return redirect(request.META.get("HTTP_REFERER") or "enrollment:declaracao_selection")

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = issued.formatted_number.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response
