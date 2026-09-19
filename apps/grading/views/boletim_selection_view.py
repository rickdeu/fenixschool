"""Selecção de aluno/trimestre para o Boletim (issue #97, RF-REL-04) --
ecrã próprio em `grading`, listando os alunos matriculados para que o
utilizador escolha um e veja o seu boletim (`boletim_view`).

Sem turma seleccionada, lista todas as turmas de uma vez (cada uma na sua
própria secção) em vez de obrigar a escolher uma primeiro -- o trimestre
continua obrigatório (um boletim é sempre de um trimestre concreto)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.academic.models import SchoolClass
from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment


def _enrollments_for(institution, school_class):
    return list(
        Enrollment.objects.filter(
            institution=institution,
            school_class=school_class,
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
        )
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def boletim_selection_view(request):
    institution = request.user.institution
    school_classes = SchoolClass.objects.filter(institution=institution).order_by("designation")

    school_class_id = request.GET.get("turma") or ""
    academic_term_id = request.GET.get("periodo") or ""

    groups = None
    if academic_term_id:
        if school_class_id:
            classes_to_show = school_classes.filter(pk=school_class_id)
        else:
            classes_to_show = school_classes
        groups = [
            {"school_class": sc, "enrollments": _enrollments_for(institution, sc)}
            for sc in classes_to_show
        ]
        if not school_class_id:
            groups = [group for group in groups if group["enrollments"]]

    return render(
        request,
        "grading/boletim_selection.html",
        {
            "school_classes": school_classes,
            "academic_terms": AcademicTerm.objects.filter(institution=institution).order_by(
                "number"
            ),
            "selected_school_class": school_class_id,
            "selected_academic_term": academic_term_id,
            "groups": groups,
        },
    )
