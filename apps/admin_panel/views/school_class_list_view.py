"""Lista de turmas, agrupadas por ano lectivo (RF-CURR-05, docs/06-
modulos-e-funcionalidades.md §6.5) -- até agora só existia como Django
Admin (issue #34); pedido directo do utilizador por um ecrã real."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.academic.models import Course, SchoolClass
from apps.core.models import AcademicYear
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("academic.view_schoolclass", raise_exception=True)
def school_class_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    academic_years = AcademicYear.objects.filter(institution=institution).order_by("-start_date")
    courses = Course.objects.filter(institution=institution).order_by("name")

    selected_academic_year_id = request.GET.get("ano_lectivo") or ""
    selected_course_id = request.GET.get("curso") or ""

    school_classes = (
        SchoolClass.objects.filter(institution=institution)
        .select_related("academic_year", "course", "curricular_year")
        .order_by("designation")
    )
    if selected_academic_year_id:
        school_classes = school_classes.filter(academic_year_id=selected_academic_year_id)
    if selected_course_id:
        school_classes = school_classes.filter(course_id=selected_course_id)

    # Agrupadas por ano lectivo -- "a lista das turmas do respectivo ano
    # lectivo" (pedido do utilizador) -- sem filtro, mostra todos os anos
    # de uma vez (cada um na sua própria secção), o filtro só restringe.
    groups = []
    for academic_year in academic_years:
        if selected_academic_year_id and str(academic_year.id) != selected_academic_year_id:
            continue
        classes_this_year = [sc for sc in school_classes if sc.academic_year_id == academic_year.id]
        if classes_this_year or selected_academic_year_id:
            groups.append({"academic_year": academic_year, "school_classes": classes_this_year})

    return render(
        request,
        "admin_panel/school_class_list.html",
        {
            "groups": groups,
            "academic_years": academic_years,
            "courses": courses,
            "selected_academic_year_id": selected_academic_year_id,
            "selected_course_id": selected_course_id,
        },
    )
