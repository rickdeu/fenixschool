"""Lista de alunos de uma turma (RF-CURR-05, docs/06-modulos-e-
funcionalidades.md §6.5) -- pedido directo do utilizador ao ver a lista de
turmas: "mas ao clicar na turma devo visualizar a lista de alunos"."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.academic.models import SchoolClass
from apps.core.view_helpers import require_institution_context
from apps.enrollment.models import Enrollment


@login_required
@permission_required("academic.view_schoolclass", raise_exception=True)
def school_class_students_view(request, school_class_id):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    school_class = get_object_or_404(SchoolClass, pk=school_class_id, institution=institution)

    enrollments = (
        Enrollment.objects.filter(institution=institution, school_class=school_class)
        .select_related("student")
        .order_by("student__first_name", "student__last_name")
    )

    return render(
        request,
        "admin_panel/school_class_students.html",
        {
            "school_class": school_class,
            "enrollments": enrollments,
        },
    )
