"""View de pré-candidatura pública (issue #102, RF-PUB-03, docs/06-modulos-e-
funcionalidades.md §6.3)."""

from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.enrollment.models import Candidate
from apps.enrollment.services import emitir_comprovativo_candidatura

from ..forms import ApplicationReceiptLookupForm, PreApplicationForm
from ..services import get_the_institution


def pre_application_view(request):
    institution = get_the_institution()
    if institution is None:
        return redirect("core:setup_wizard")

    if request.method == "POST":
        form = PreApplicationForm(request.POST, institution=institution)
        if form.is_valid():
            candidate = form.save(commit=False)
            candidate.institution = institution
            candidate.origin_node_id = get_current_node_id()
            candidate.status = Candidate.Status.PENDING
            candidate.save()
            emitir_comprovativo_candidatura(
                candidate=candidate, origin_node_id=get_current_node_id()
            )
            return render(
                request, "public_site/pre_application_success.html", {"candidate": candidate}
            )
    else:
        form = PreApplicationForm(institution=institution)

    return render(request, "public_site/pre_application_form.html", {"form": form})


def application_receipt_view(request):
    """ "Voltar a emitir quando necessário" (pedido do utilizador):
    self-service público, sem autenticação -- pelo número de documento
    apresentado na candidatura, o único "segredo" que o candidato tem à
    mão sem ter guardado nenhum link."""

    institution = get_the_institution()

    if request.method == "POST":
        form = ApplicationReceiptLookupForm(request.POST, institution=institution)
        if form.is_valid():
            candidate = form.cleaned_data["candidate"]
            pdf = emitir_comprovativo_candidatura(
                candidate=candidate, origin_node_id=get_current_node_id()
            )
            return HttpResponse(pdf, content_type="application/pdf")
    else:
        initial = {"document_number": request.GET.get("documento", "")}
        form = ApplicationReceiptLookupForm(initial=initial, institution=institution)

    return render(request, "public_site/application_receipt_lookup.html", {"form": form})
