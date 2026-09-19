"""Mapa de faltas por turma (issue #69, RF-FREQ-04) -- para Direção
Pedagógica/Secretaria/Administrador da Instituição.

Sem filtro seleccionado, mostra todas as turmas de uma vez (cada uma na
sua própria secção) em vez de obrigar a escolher uma primeiro -- o filtro
continua disponível para restringir a uma só."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.academic.models import SchoolClass

from ..services import mapa_faltas_turma


@login_required
@permission_required("attendance.view_attendance", raise_exception=True)
def attendance_map_view(request):
    institution = request.user.institution
    school_classes = SchoolClass.objects.filter(institution=institution).order_by("designation")

    def _group(sc):
        return {
            "school_class": sc,
            "rows": mapa_faltas_turma(institution=institution, school_class=sc),
        }

    school_class_id = request.GET.get("turma") or ""
    if school_class_id:
        school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)
        groups = [_group(school_class)]
    else:
        groups = [group for sc in school_classes if (group := _group(sc))["rows"]]

    return render(
        request,
        "attendance/attendance_map.html",
        {
            "school_classes": school_classes,
            "selected_school_class": school_class_id,
            "groups": groups,
        },
    )
