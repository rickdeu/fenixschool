"""Justificar uma falta concreta, com anexo opcional (issue #67,
RF-FREQ-02)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Attendance
from ..services import EstadoInvalidoParaJustificacaoError, justificar_falta


@login_required
@permission_required("attendance.change_attendance", raise_exception=True)
def justify_absence_view(request, attendance_id):
    institution = request.user.institution
    attendance = get_object_or_404(
        Attendance.objects.select_related("student", "schedule__subject"),
        pk=attendance_id,
        institution=institution,
    )

    if request.method == "POST":
        text = request.POST.get("justification_text", "")
        attachment = request.FILES.get("justification_attachment")
        try:
            justificar_falta(
                attendance=attendance,
                text=text,
                justified_by=request.user,
                attachment=attachment,
            )
        except EstadoInvalidoParaJustificacaoError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Falta justificada com sucesso.")
            return redirect("attendance:absence_list")

    return render(request, "attendance/justify_absence.html", {"attendance": attendance})
