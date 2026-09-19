"""Frequência do educando (issue #69, RF-FREQ-04) -- âmbito
automaticamente restrito aos próprios educandos do Encarregado de
Educação, mesmo selector de educando do dashboard (issue #52)."""

from django.shortcuts import render

from apps.attendance.services import mapa_faltas_aluno
from apps.enrollment.models import Enrollment

from ..permissions import guardian_required
from ..services import get_own_students, resolve_selected_student


@guardian_required
def attendance_view(request):
    students = get_own_students(request.user)
    selected_student = resolve_selected_student(request, students)

    summary = None
    if selected_student is not None:
        enrollment = (
            Enrollment.objects.filter(
                institution=request.user.institution,
                student=selected_student,
                status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
            )
            .select_related("curricular_year")
            .first()
        )
        if enrollment is not None:
            summary = mapa_faltas_aluno(enrollment=enrollment)

    return render(
        request,
        "guardian_portal/attendance.html",
        {
            "students": students,
            "selected_student": selected_student,
            "summary": summary,
        },
    )
