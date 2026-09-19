"""Acesso ao anexo de justificação de falta, sempre mediado pela aplicação
(issue #67, RF-FREQ-02/docs/09-seguranca-e-privacidade.md §9.3: "nunca URL
pública directa") -- nunca `{{ attendance.justification_attachment.url }}`
em nenhum template; o Nginx também recusa `/media/attendance/
justifications/` directamente (ver docker/nginx/app.conf.template)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from ..models import Attendance


@login_required
@permission_required("attendance.view_attendance", raise_exception=True)
def justification_attachment_view(request, attendance_id):
    institution = request.user.institution
    attendance = get_object_or_404(Attendance, pk=attendance_id, institution=institution)

    if not attendance.justification_attachment:
        raise Http404

    return FileResponse(
        attendance.justification_attachment.open("rb"),
        as_attachment=True,
        filename=attendance.justification_attachment.name.rsplit("/", 1)[-1],
    )
