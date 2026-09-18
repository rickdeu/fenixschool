"""Lista de pautas (issue #60, RF-AVAL-04) -- ecrã próprio em `grading`,
substituindo as antigas acções do Django Admin (nunca usado por
utilizadores reais). Mostra o formulário de selecção manual e a lista de
pautas já existentes; ver/editar/homologar uma pauta concreta acontece em
`pauta_detail_view`."""

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.shortcuts import render

from apps.academic.models import SchoolClass, Subject
from apps.core.models import AcademicTerm

from ..models import EvaluationType, Grade


def _list_occurrences(institution):
    """Every distinct turma/disciplina/tipo/trimestre combination that
    already has notas lançadas -- lets the user pick a pauta to view
    instead of having to guess a valid combination via the filter form."""

    occurrences = list(
        Grade.objects.filter(institution=institution)
        .values(
            "school_class_id",
            "school_class__designation",
            "subject_id",
            "subject__name",
            "evaluation_type_id",
            "evaluation_type__name",
            "academic_term_id",
        )
        .annotate(
            total=Count("id"),
            closed=Count("id", filter=Q(is_grade_report_closed=True)),
        )
        .order_by(
            "school_class__designation",
            "subject__name",
            "academic_term_id",
            "evaluation_type__name",
        )
    )

    term_labels = {
        term.id: str(term)
        for term in AcademicTerm.objects.filter(
            institution=institution,
            id__in={row["academic_term_id"] for row in occurrences},
        )
    }
    for row in occurrences:
        row["academic_term_label"] = term_labels.get(row["academic_term_id"], "")
        row["is_closed"] = row["total"] > 0 and row["closed"] == row["total"]
    return occurrences


@login_required
@permission_required("grading.change_grade", raise_exception=True)
def pauta_management_view(request):
    institution = request.user.institution

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
            "occurrences": _list_occurrences(institution),
        },
    )
