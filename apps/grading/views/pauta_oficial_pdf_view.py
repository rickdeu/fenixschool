"""Exportação da Pauta em PDF oficial (issue #96, RF-REL-03) -- reaproveita
a mesma selecção turma/disciplina/tipo/trimestre e as mesmas notas que
`pauta_detail_view` já mostra no ecrã, delegando a numeração/auditoria/
renderização a `apps.reports.services.gerar_pauta_oficial_pdf`."""

import uuid

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from apps.academic.models import SchoolClass, Subject
from apps.core.models import AcademicTerm
from apps.reports.services import gerar_pauta_oficial_pdf

from ..models import EvaluationType, Grade


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def pauta_oficial_pdf_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    institution = request.user.institution
    school_class = get_object_or_404(
        SchoolClass, pk=request.POST.get("turma"), institution=institution
    )
    subject = get_object_or_404(Subject, pk=request.POST.get("disciplina"), institution=institution)
    evaluation_type = get_object_or_404(
        EvaluationType, pk=request.POST.get("tipo"), institution=institution
    )
    academic_term = get_object_or_404(
        AcademicTerm, pk=request.POST.get("periodo"), institution=institution
    )

    grades = list(
        Grade.objects.filter(
            institution=institution,
            school_class=school_class,
            subject=subject,
            evaluation_type=evaluation_type,
            academic_term=academic_term,
        )
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )

    issued, pdf = gerar_pauta_oficial_pdf(
        school_class=school_class,
        subject=subject,
        evaluation_type=evaluation_type,
        academic_term=academic_term,
        grades=grades,
        issued_by=request.user,
        origin_node_id=uuid.uuid4(),
    )

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = issued.formatted_number.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response
