"""View de pré-candidatura pública (issue #102, RF-PUB-03, docs/06-modulos-e-
funcionalidades.md §6.3)."""

from django.shortcuts import redirect, render

from apps.core.context import get_current_node_id
from apps.enrollment.models import Candidate

from ..forms import PreApplicationForm
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
            return render(
                request, "public_site/pre_application_success.html", {"candidate": candidate}
            )
    else:
        form = PreApplicationForm(institution=institution)

    return render(request, "public_site/pre_application_form.html", {"form": form})
