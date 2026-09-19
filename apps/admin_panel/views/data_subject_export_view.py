"""Ecrã de exportação de dados de um titular (issue #144, RF-.../9.1, Lei
22/11): direito de acesso/rectificação -- exportação completa e legível
dos dados pessoais de um Aluno ou Encarregado de Educação, a pedido.

Restrito ao Administrador da Instituição (o mesmo `core.change_institution`
já usado por outros ecrãs sensíveis desta app, como `backup_list_view`):
um pedido de acesso ao abrigo da Lei 22/11 não é trabalho de rotina da
Secretaria.

`Funcionário` (RH) fica de fora por agora -- o módulo `hr` ainda não tem
modelos (M3).
"""

import json

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.core.view_helpers import require_institution_context
from apps.enrollment.models import Guardian, Student

from ..services import export_guardian_personal_data, export_student_personal_data

SECTION_LABELS = {
    "aluno": "Aluno",
    "encarregados_de_educacao": "Encarregados de Educação",
    "matriculas": "Matrículas",
    "notas": "Notas",
    "medias_finais": "Médias finais",
    "presencas": "Presenças",
    "encarregado_de_educacao": "Encarregado de Educação",
    "alunos_associados": "Alunos associados",
}


def _sections(data: dict) -> list[tuple[str, object]]:
    return [(SECTION_LABELS.get(key, key), value) for key, value in data.items()]


@login_required
@permission_required("core.change_institution", raise_exception=True)
def data_subject_export_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    query = request.GET.get("q", "").strip()
    students = []
    guardians = []
    if query:
        student_filters = (
            Q(document_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        students = list(Student.objects.filter(institution=institution).filter(student_filters))
        # `document_number` cifrado (issue #141) só suporta igualdade exacta
        # -- `full_name__icontains` continua a funcionar normalmente.
        guardian_filters = Q(full_name__icontains=query) | Q(document_number=query)
        guardians = list(Guardian.objects.filter(institution=institution).filter(guardian_filters))

    return render(
        request,
        "admin_panel/data_subject_export.html",
        {"query": query, "students": students, "guardians": guardians},
    )


def _json_download(data: dict, *, filename: str) -> HttpResponse:
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@permission_required("core.change_institution", raise_exception=True)
def data_subject_export_student_view(request, student_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    student = get_object_or_404(Student, pk=student_id, institution=request.institution)
    data = export_student_personal_data(student)

    if request.GET.get("formato") == "json":
        return _json_download(data, filename=f"dados-pessoais-aluno-{student.student_number}.json")

    return render(
        request,
        "admin_panel/data_subject_export_detail.html",
        {"title": f"Dados pessoais de {student}", "sections": _sections(data)},
    )


@login_required
@permission_required("core.change_institution", raise_exception=True)
def data_subject_export_guardian_view(request, guardian_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    guardian = get_object_or_404(Guardian, pk=guardian_id, institution=request.institution)
    data = export_guardian_personal_data(guardian)

    if request.GET.get("formato") == "json":
        return _json_download(data, filename=f"dados-pessoais-encarregado-{guardian.pk}.json")

    return render(
        request,
        "admin_panel/data_subject_export_detail.html",
        {"title": f"Dados pessoais de {guardian}", "sections": _sections(data)},
    )
