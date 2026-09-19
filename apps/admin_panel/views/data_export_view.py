"""Ecrã de exportações normativas (issue #117, RF-ADM-05): backup manual e
exportação por entidade (Alunos, Matrículas, Notas) em CSV/JSON/PDF.

Restrito ao Administrador da Instituição (`core.change_institution`, o
mesmo nível já usado pelos outros ecrãs sensíveis desta app).

`Financeiro` fica de fora por agora -- o módulo `finance` ainda não tem
modelos (M3).
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import render

from apps.core.view_helpers import require_institution_context

from ..exports import EXPORT_RENDERERS, EXPORTABLE_ENTITIES, export_entity


@login_required
@permission_required("core.change_institution", raise_exception=True)
def data_export_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    entity_key = request.GET.get("entidade")
    formato = request.GET.get("formato")
    if entity_key and formato:
        if entity_key not in EXPORTABLE_ENTITIES or formato not in EXPORT_RENDERERS:
            raise Http404
        return export_entity(entity_key, formato, request.institution)

    return render(
        request,
        "admin_panel/data_export.html",
        {
            "entities": [
                {"key": key, "label": entity["label"]}
                for key, entity in EXPORTABLE_ENTITIES.items()
            ],
            "formats": list(EXPORT_RENDERERS),
        },
    )
