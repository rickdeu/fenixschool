"""Ver/editar/homologar uma pauta concreta (issue #60, RF-AVAL-04) -- as
notas continuam editáveis (correcção administrativa, não exige ser o
docente agendado -- ver `services.atualizar_nota_pauta`) até à pauta ser
homologada; a partir daí `Grade.save()` bloqueia a edição
(`GradeReportClosedError`) até uma reabertura justificada."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import SchoolClass, Subject
from apps.core.models import AcademicTerm

from ..models import EvaluationType, Grade
from ..services import ReaberturaSemJustificacaoError, homologar_pauta, reabrir_pauta


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def pauta_detail_view(request):
    institution = request.user.institution
    school_class = get_object_or_404(
        SchoolClass, pk=request.GET.get("turma"), institution=institution
    )
    subject = get_object_or_404(Subject, pk=request.GET.get("disciplina"), institution=institution)
    evaluation_type = get_object_or_404(
        EvaluationType, pk=request.GET.get("tipo"), institution=institution
    )
    academic_term = get_object_or_404(
        AcademicTerm, pk=request.GET.get("periodo"), institution=institution
    )

    if request.method == "POST":
        grade_ids = request.POST.getlist("grade_ids")
        grades_qs = Grade.objects.filter(institution=institution, pk__in=grade_ids)
        if request.POST.get("action") == "homologar":
            count = homologar_pauta(grades_qs, user=request.user)
            messages.success(request, f"{count} nota(s) homologada(s) e fechada(s).")
        elif request.POST.get("action") == "reabrir":
            reason = request.POST.get("reason", "")
            try:
                count = reabrir_pauta(grades_qs, user=request.user, reason=reason)
            except ReaberturaSemJustificacaoError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, f"{count} nota(s) reaberta(s).")
        return redirect(request.get_full_path())

    rows = list(
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
    all_closed = bool(rows) and all(grade.is_grade_report_closed for grade in rows)
    any_closed = any(grade.is_grade_report_closed for grade in rows)

    return render(
        request,
        "grading/pauta_detail.html",
        {
            "school_class": school_class,
            "subject": subject,
            "evaluation_type": evaluation_type,
            "academic_term": academic_term,
            "rows": rows,
            "all_closed": all_closed,
            "any_closed": any_closed,
        },
    )
