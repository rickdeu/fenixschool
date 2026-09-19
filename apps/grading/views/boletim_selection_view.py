"""Selecção de aluno/trimestre para o Boletim (issue #97, RF-REL-04) --
ecrã próprio em `grading`, listando os alunos matriculados na turma
escolhida para que o utilizador escolha um e veja o seu boletim
(`boletim_view`)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.academic.models import SchoolClass
from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def boletim_selection_view(request):
    institution = request.user.institution

    school_class_id = request.GET.get("turma") or ""
    academic_term_id = request.GET.get("periodo") or ""

    enrollments = None
    if school_class_id and academic_term_id:
        enrollments = (
            Enrollment.objects.filter(
                institution=institution,
                school_class_id=school_class_id,
                status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
            )
            .select_related("student")
            .order_by("student__first_name", "student__last_name")
        )

    return render(
        request,
        "grading/boletim_selection.html",
        {
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "academic_terms": AcademicTerm.objects.filter(institution=institution).order_by(
                "number"
            ),
            "selected_school_class": school_class_id,
            "selected_academic_term": academic_term_id,
            "enrollments": enrollments,
        },
    )
