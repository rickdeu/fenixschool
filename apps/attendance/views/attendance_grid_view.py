"""Grelha de marcação de presença de uma turma inteira, num horário/dia
(issue #66, RF-FREQ-01): marcação em lote, poucos cliques."""

import uuid
from datetime import date as date_cls

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import Schedule
from apps.enrollment.models import Enrollment

from ..models import Attendance
from ..permissions import docente_required
from ..services import DocenteNaoAssociadoError, registar_presencas


@docente_required
def attendance_grid_view(request):
    institution = request.user.institution
    schedule = get_object_or_404(
        Schedule,
        pk=request.GET.get("horario") or request.POST.get("horario"),
        institution=institution,
    )

    # Same object-level scoping `registar_presencas` itself enforces on
    # save -- checked again here, up front, so a docente can't view (not
    # just save into) another docente's turma by tampering with the query
    # string. Super Administrador bypasses this too ("acesso a tudo").
    if not request.user.is_superuser and schedule.teacher_id != request.user.id:
        raise PermissionDenied

    date_str = request.GET.get("data") or request.POST.get("data")
    try:
        attendance_date = date_cls.fromisoformat(date_str)
    except (TypeError, ValueError):
        attendance_date = date_cls.today()

    if request.method == "POST":
        statuses = {
            key.removeprefix("status_"): value
            for key, value in request.POST.items()
            if key.startswith("status_")
        }
        try:
            registar_presencas(
                teacher=request.user,
                schedule=schedule,
                date=attendance_date,
                statuses=statuses,
                origin_node_id=uuid.uuid4(),
            )
        except DocenteNaoAssociadoError:
            messages.error(request, "Não está associado a este horário.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Presenças gravadas.")
        return redirect(
            f"{request.path}?horario={schedule.id}&data={attendance_date.isoformat()}"
        )

    enrollments = (
        Enrollment.objects.filter(
            institution=institution,
            school_class=schedule.school_class,
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
        )
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )
    existing_by_enrollment_id = {
        attendance.enrollment_id: attendance
        for attendance in Attendance.objects.filter(
            institution=institution, schedule=schedule, date=attendance_date
        )
    }
    rows = [
        {"enrollment": enrollment, "attendance": existing_by_enrollment_id.get(enrollment.id)}
        for enrollment in enrollments
    ]

    return render(
        request,
        "attendance/attendance_grid.html",
        {
            "schedule": schedule,
            "date": attendance_date,
            "rows": rows,
            "status_choices": Attendance.Status.choices,
            "default_status": Attendance.Status.PRESENT,
        },
    )
