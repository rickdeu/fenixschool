"""Mapa de faltas por horário do docente (issue #69, RF-FREQ-04) -- só os
alunos das turmas/disciplinas que o próprio docente lecciona (mesmo âmbito
de `get_docente_schedule_slots`, issue #66)."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from apps.academic.models import Schedule
from apps.enrollment.models import Enrollment

from ..permissions import docente_required
from ..services import calcular_assiduidade, get_docente_schedule_slots


@docente_required
def docente_attendance_map_view(request):
    institution = request.user.institution

    schedule_id = request.GET.get("horario") or ""
    rows = None
    schedule = None
    if schedule_id:
        schedule = get_object_or_404(Schedule, pk=schedule_id, institution=institution)
        if not request.user.is_superuser and schedule.teacher_id != request.user.id:
            raise PermissionDenied

        enrollments = (
            Enrollment.objects.filter(
                institution=institution,
                school_class=schedule.school_class,
                status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
            )
            .select_related("student")
            .order_by("student__first_name", "student__last_name")
        )
        rows = [
            {
                "enrollment": enrollment,
                **calcular_assiduidade(enrollment=enrollment, subject=schedule.subject),
            }
            for enrollment in enrollments
        ]

    return render(
        request,
        "attendance/docente_attendance_map.html",
        {
            "schedules": get_docente_schedule_slots(request.user),
            "selected_schedule": schedule_id,
            "schedule": schedule,
            "rows": rows,
        },
    )
