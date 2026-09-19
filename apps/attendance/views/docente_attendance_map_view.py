"""Mapa de faltas por horário do docente (issue #69, RF-FREQ-04) -- só os
alunos das turmas/disciplinas que o próprio docente lecciona (mesmo âmbito
de `get_docente_schedule_slots`, issue #66).

Sem horário seleccionado, mostra todos de uma vez (cada um na sua própria
secção) em vez de obrigar a escolher um primeiro -- o filtro continua
disponível para restringir a um só."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from apps.academic.models import Schedule
from apps.enrollment.models import Enrollment

from ..permissions import docente_required
from ..services import calcular_assiduidade, get_docente_schedule_slots


def _rows_for(institution, schedule):
    enrollments = (
        Enrollment.objects.filter(
            institution=institution,
            school_class=schedule.school_class,
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
        )
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )
    return [
        {
            "enrollment": enrollment,
            **calcular_assiduidade(enrollment=enrollment, subject=schedule.subject),
        }
        for enrollment in enrollments
    ]


@docente_required
def docente_attendance_map_view(request):
    institution = request.user.institution
    schedules = get_docente_schedule_slots(request.user)

    schedule_id = request.GET.get("horario") or ""
    if schedule_id:
        schedule = get_object_or_404(Schedule, pk=schedule_id, institution=institution)
        if not request.user.is_superuser and schedule.teacher_id != request.user.id:
            raise PermissionDenied
        groups = [{"schedule": schedule, "rows": _rows_for(institution, schedule)}]
    else:
        groups = [{"schedule": slot, "rows": _rows_for(institution, slot)} for slot in schedules]
        groups = [group for group in groups if group["rows"]]

    return render(
        request,
        "attendance/docente_attendance_map.html",
        {
            "schedules": schedules,
            "selected_schedule": schedule_id,
            "groups": groups,
        },
    )
