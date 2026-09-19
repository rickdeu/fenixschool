"""Selecção de turma para emissão de Declarações (issue #94, RF-REL-01) --
lista os alunos matriculados na turma escolhida, cada um com um botão por
tipo de declaração (activo apenas quando o estado da matrícula é
compatível -- ver `apps.enrollment.services.emitir_declaracao`).

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


@login_required
@permission_required("reports.add_issueddocument", raise_exception=True)
def declaracao_selection_view(request):
    institution = request.user.institution

    school_class_id = request.GET.get("turma") or ""
    enrollments = None
    if school_class_id:
        enrollments = (
            Enrollment.objects.filter(institution=institution, school_class_id=school_class_id)
            .select_related("student")
            .order_by("student__first_name", "student__last_name")
        )

    return render(
        request,
        "enrollment/declaracao_selection.html",
        {
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "selected_school_class": school_class_id,
            "enrollments": enrollments,
            "declaracao_matricula": DECLARACAO_MATRICULA,
            "declaracao_frequencia": DECLARACAO_FREQUENCIA,
            "declaracao_conclusao": DECLARACAO_CONCLUSAO,
            "active_statuses": {Enrollment.Status.ACTIVE, Enrollment.Status.PENDING},
            "completed_status": Enrollment.Status.COMPLETED,
        },
    )
