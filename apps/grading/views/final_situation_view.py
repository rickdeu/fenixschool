"""Situação final dos alunos (issue #62, RF-AVAL-07) -- ecrã próprio,
substituindo a antiga acção do Django Admin (nunca usado por utilizadores
reais)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from apps.academic.models import SchoolClass
from apps.enrollment.models import Enrollment

from ..models import FinalSituation
from ..services import calcular_situacao_final

_ACTIVE_STATUSES = [Enrollment.Status.PENDING, Enrollment.Status.ACTIVE]


def _list_occurrences(institution):
    """Every turma with active matrículas, and how many already have a
    situação final calculada -- lets the user pick a turma to work on
    instead of having to guess one via the filter form."""

    occurrences = []
    for school_class in SchoolClass.objects.filter(institution=institution).order_by(
        "designation"
    ):
        total = Enrollment.objects.filter(
            institution=institution, school_class=school_class, status__in=_ACTIVE_STATUSES
        ).count()
        if total == 0:
            continue
        calculated = FinalSituation.objects.filter(
            institution=institution, enrollment__school_class=school_class
        ).count()
        occurrences.append(
            {
                "school_class": school_class,
                "total": total,
                "calculated": calculated,
                "pending": total - calculated,
            }
        )
    return occurrences


@login_required
@permission_required("grading.view_finalsituation", raise_exception=True)
def final_situation_view(request):
    institution = request.user.institution

    if request.method == "POST":
        enrollment_ids = request.POST.getlist("enrollment_ids")
        enrollments = Enrollment.objects.filter(institution=institution, pk__in=enrollment_ids)
        for enrollment in enrollments:
            calcular_situacao_final(enrollment)
        messages.success(
            request, f"Situação final calculada para {enrollments.count()} matrícula(s)."
        )
        return redirect(request.get_full_path())

    school_class_id = request.GET.get("turma") or ""
    rows = None

    if school_class_id:
        enrollments = (
            Enrollment.objects.filter(
                institution=institution,
                school_class_id=school_class_id,
                status__in=_ACTIVE_STATUSES,
            )
            .select_related("student", "school_class")
            .order_by("student__first_name", "student__last_name")
        )
        situations_by_enrollment_id = {
            situation.enrollment_id: situation
            for situation in FinalSituation.objects.filter(
                institution=institution, enrollment__in=enrollments
            ).prefetch_related("failed_subjects")
        }
        rows = [
            {"enrollment": enrollment, "situation": situations_by_enrollment_id.get(enrollment.id)}
            for enrollment in enrollments
        ]

    return render(
        request,
        "grading/final_situation.html",
        {
            "rows": rows,
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "selected_school_class": school_class_id,
            "occurrences": _list_occurrences(institution),
        },
    )
