"""Homologação/reabertura de pautas (issue #60, RF-AVAL-04) -- ecrã próprio
em `admin_panel`/`grading`, substituindo as antigas acções do Django Admin
(nunca usado por utilizadores reais)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import SchoolClass, Subject
from apps.core.models import AcademicTerm

from ..models import EvaluationType, Grade
from ..services import ReaberturaSemJustificacaoError, homologar_pauta, reabrir_pauta


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def pauta_management_view(request):
    institution = request.user.institution

    school_class_id = request.GET.get("turma") or ""
    subject_id = request.GET.get("disciplina") or ""
    evaluation_type_id = request.GET.get("tipo") or ""
    academic_term_id = request.GET.get("periodo") or ""

    rows = None
    all_closed = any_closed = False

    if school_class_id and subject_id and evaluation_type_id and academic_term_id:
        school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)
        subject = get_object_or_404(Subject, pk=subject_id, institution=institution)
        evaluation_type = get_object_or_404(
            EvaluationType, pk=evaluation_type_id, institution=institution
        )
        academic_term = get_object_or_404(
            AcademicTerm, pk=academic_term_id, institution=institution
        )
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

    return render(
        request,
        "grading/pauta_management.html",
        {
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "subjects": Subject.objects.filter(institution=institution).order_by("name"),
            "evaluation_types": EvaluationType.objects.filter(institution=institution).order_by(
                "name"
            ),
            "academic_terms": AcademicTerm.objects.filter(institution=institution).order_by(
                "number"
            ),
            "selected_school_class": school_class_id,
            "selected_subject": subject_id,
            "selected_evaluation_type": evaluation_type_id,
            "selected_academic_term": academic_term_id,
            "rows": rows,
            "all_closed": all_closed,
            "any_closed": any_closed,
        },
    )
