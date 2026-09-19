"""Lista de faltas por justificar/já justificadas de uma turma (issue #67,
RF-FREQ-02) -- ponto de entrada para "processamento final manual pela
Secretaria" (docs/06-modulos-e-funcionalidades.md §6.13) de um pedido de
justificação vindo do Encarregado de Educação."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.academic.models import SchoolClass

from ..models import Attendance


@login_required
@permission_required("attendance.change_attendance", raise_exception=True)
def absence_list_view(request):
    institution = request.user.institution

    school_class_id = request.GET.get("turma") or ""
    absences = None
    if school_class_id:
        school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)
        absences = (
            Attendance.objects.filter(
                institution=institution,
                schedule__school_class=school_class,
                status__in=[Attendance.Status.ABSENT, Attendance.Status.JUSTIFIED_ABSENT],
            )
            .select_related("student", "schedule__subject")
            .order_by("-date", "student__first_name", "student__last_name")
        )

    return render(
        request,
        "attendance/absence_list.html",
        {
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "selected_school_class": school_class_id,
            "absences": absences,
        },
    )
