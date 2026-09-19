"""Selecção de turma para emissão de Declarações (issue #94, RF-REL-01) --
lista os alunos matriculados, cada um com um botão por tipo de declaração
(activo apenas quando o estado da matrícula é compatível -- ver
`apps.enrollment.services.emitir_declaracao`).

Sem turma seleccionada, mostra todas de uma vez (cada uma na sua própria
secção) em vez de obrigar a escolher uma primeiro -- o filtro continua
disponível para restringir a uma só.

Gate de permissão em `reports.add_issueddocument` (não
`enrollment.view_enrollment`): este último já está concedido ao
Encarregado de Educação (issue #29), mas apenas para *os seus próprios*
educandos -- o queryset aqui não aplica esse âmbito (`for_guardian`), por
ser um ecrã operacional para quem emite documentos, não o self-service do
Encarregado. Gatilhar pela mesma permissão da própria emissão evita expor
a lista inteira de alunos de uma turma a quem só devia ver os seus."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.academic.models import SchoolClass

from ..models import Enrollment
from ..services import DECLARACAO_CONCLUSAO, DECLARACAO_FREQUENCIA, DECLARACAO_MATRICULA


def _enrollments_for(institution, school_class):
    return list(
        Enrollment.objects.filter(institution=institution, school_class=school_class)
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )


@login_required
@permission_required("reports.add_issueddocument", raise_exception=True)
def declaracao_selection_view(request):
    institution = request.user.institution
    school_classes = SchoolClass.objects.filter(institution=institution).order_by("designation")

    school_class_id = request.GET.get("turma") or ""
    if school_class_id:
        classes_to_show = school_classes.filter(pk=school_class_id)
    else:
        classes_to_show = school_classes

    groups = [
        {"school_class": sc, "enrollments": _enrollments_for(institution, sc)}
        for sc in classes_to_show
    ]
    if not school_class_id:
        groups = [group for group in groups if group["enrollments"]]

    return render(
        request,
        "enrollment/declaracao_selection.html",
        {
            "school_classes": school_classes,
            "selected_school_class": school_class_id,
            "groups": groups,
            "declaracao_matricula": DECLARACAO_MATRICULA,
            "declaracao_frequencia": DECLARACAO_FREQUENCIA,
            "declaracao_conclusao": DECLARACAO_CONCLUSAO,
            "active_statuses": {Enrollment.Status.ACTIVE, Enrollment.Status.PENDING},
            "completed_status": Enrollment.Status.COMPLETED,
        },
    )
