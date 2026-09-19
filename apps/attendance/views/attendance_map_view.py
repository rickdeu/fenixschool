"""Mapa de faltas por turma (issue #69, RF-FREQ-04) -- para Direção
Pedagógica/Secretaria/Administrador da Instituição."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.academic.models import SchoolClass

from ..services import mapa_faltas_turma


@login_required
@permission_required("attendance.view_attendance", raise_exception=True)
def attendance_map_view(request):
    institution = request.user.institution

    school_class_id = request.GET.get("turma") or ""
    rows = None
    if school_class_id:
        school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)
        rows = mapa_faltas_turma(institution=institution, school_class=school_class)

    return render(
        request,
        "attendance/attendance_map.html",
        {
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "selected_school_class": school_class_id,
            "rows": rows,
        },
    )
