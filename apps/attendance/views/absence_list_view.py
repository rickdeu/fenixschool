"""Lista de faltas por justificar/já justificadas de uma turma (issue #67,
RF-FREQ-02) -- ponto de entrada para "processamento final manual pela
Secretaria" (docs/06-modulos-e-funcionalidades.md §6.13) de um pedido de
justificação vindo do Encarregado de Educação.

Sem filtro seleccionado, mostra todas as turmas com faltas de uma vez
(cada uma na sua própria secção) em vez de obrigar a escolher uma
primeiro -- o filtro continua disponível para restringir a uma só."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.academic.models import SchoolClass

from ..models import Attendance


def _absences_for(institution, school_class):
    return list(
        Attendance.objects.filter(
            institution=institution,
            schedule__school_class=school_class,
            status__in=[Attendance.Status.ABSENT, Attendance.Status.JUSTIFIED_ABSENT],
        )
        .select_related("student", "schedule__subject")
        .order_by("-date", "student__first_name", "student__last_name")
    )


@login_required
@permission_required("attendance.change_attendance", raise_exception=True)
def absence_list_view(request):
    institution = request.user.institution
    school_classes = SchoolClass.objects.filter(institution=institution).order_by("designation")

    def _group(sc):
        return {"school_class": sc, "absences": _absences_for(institution, sc)}

    school_class_id = request.GET.get("turma") or ""
    if school_class_id:
        school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)
        groups = [_group(school_class)]
    else:
        groups = [group for sc in school_classes if (group := _group(sc))["absences"]]

    return render(
        request,
        "attendance/absence_list.html",
        {
            "school_classes": school_classes,
            "selected_school_class": school_class_id,
            "groups": groups,
        },
    )
