"""Painel único de configuração da instituição (issue #114, RF-ADM-02,
docs/02-requisitos-funcionais.md §2.1).

Agrega os ecrãs de configuração já existentes -- todos com ecrã dedicado
próprio, excepto "tabelas de preços" (RF-INST-08), assinalada como
indisponível: `finance.TabelaPrecos` (issue #70) ainda não existe, nada
real para ligar.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.urls import reverse

from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("core.change_institution", raise_exception=True)
def institution_config_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    sections = [
        {
            "title": "Dados da instituição",
            "description": "Nome, NIF, morada, contactos, logótipo, apresentação (RF-INST-01).",
            "url": reverse("admin_panel:institution_edit"),
            "available": True,
        },
        {
            "title": "Anos lectivos e períodos",
            "description": "Datas, ano lectivo corrente, trimestres/semestres (RF-INST-03/04).",
            "url": reverse("admin_panel:academic_year_list"),
            "available": True,
        },
        {
            "title": "Ciclos lectivos",
            "description": "1.º/2.º Ciclo e a sua relação com os cursos (RF-INST-05).",
            "url": reverse("admin_panel:academic_cycle_list"),
            "available": True,
        },
        {
            "title": "Fórmula de cálculo de média",
            "description": "Pesos de MAC/Prova Trimestral/Exame por omissão (RF-INST-06).",
            "url": reverse("admin_panel:grading_formula_config"),
            "available": True,
        },
        {
            "title": "Feriados e dias não lectivos",
            "description": "Calendário de feriados nacionais/provinciais (RF-INST-07).",
            "url": reverse("admin_panel:non_teaching_day_list"),
            "available": True,
        },
        {
            "title": "Tabelas de preços",
            "description": "Propinas, emolumentos, taxas e multas por atraso (RF-INST-08).",
            "url": None,
            "available": False,
            "unavailable_reason": "Ainda não implementado -- issue #70.",
        },
    ]

    return render(request, "admin_panel/institution_config.html", {"sections": sections})
