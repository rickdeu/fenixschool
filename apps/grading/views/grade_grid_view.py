"""Grelha de lançamento de notas de uma turma inteira (issue #59,
docs/06-modulos-e-funcionalidades.md §6.6): lançamento linha-a-linha via
HTMX, sem recarregar a página completa.
"""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from apps.academic.models import Schedule, SchoolClass, Subject
from apps.core.models import AcademicTerm
from apps.enrollment.models import Enrollment

from ..models import EvaluationType, Grade
from ..permissions import docente_required


@docente_required
def grade_grid_view(request):
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

    # Same object-level scoping `lancar_ou_atualizar_nota` itself enforces
    # -- checked again here, up front, so a docente can't view (not just
    # save into) a turma/disciplina they don't teach by tampering with the
    # query string. A Super Administrador bypasses this too ("acesso a
    # tudo, sem restrição alguma") -- they are never actually scheduled to
    # teach anything themselves.
    if not request.user.is_superuser:
        is_associated = Schedule.objects.filter(
            institution=institution,
            teacher=request.user,
            school_class=school_class,
            subject=subject,
        ).exists()
        if not is_associated:
            raise PermissionDenied

    enrollments = (
        Enrollment.objects.filter(
            institution=institution,
            school_class=school_class,
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE],
        )
        .select_related("student")
        .order_by("student__last_name", "student__first_name")
    )
    existing_grades_by_student_id = {
        grade.student_id: grade
        for grade in Grade.objects.filter(
            institution=institution,
            subject=subject,
            evaluation_type=evaluation_type,
            academic_term=academic_term,
            enrollment__in=enrollments,
        )
    }
    rows = [
        {
            "enrollment": enrollment,
            "grade": existing_grades_by_student_id.get(enrollment.student_id),
        }
        for enrollment in enrollments
    ]

    return render(
        request,
        "grading/grade_grid.html",
        {
            "school_class": school_class,
            "subject": subject,
            "evaluation_type": evaluation_type,
            "academic_term": academic_term,
            "rows": rows,
        },
    )
