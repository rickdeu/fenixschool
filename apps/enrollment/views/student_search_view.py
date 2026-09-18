"""View de busca de aluno para matrícula (issue #47, RF-MAT-04)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import render

from ..forms import StudentSearchForm
from ..models import Student


@login_required
@permission_required("enrollment.view_student", raise_exception=True)
def student_search_view(request):
    """ "Inscrições → Matrículas → Nova Matrícula": localizar o aluno por
    número de aluno, número de documento ou nome (RF-MAT-04)."""
    institution = request.institution
    search_form = StudentSearchForm(request.GET or None)
    students = Student.objects.none()

    if search_form.is_valid() and search_form.cleaned_data["q"]:
        query = search_form.cleaned_data["q"]
        filters = (
            Q(document_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
        if query.isdigit():
            # `student_number` is an IntegerField -- only add this branch for
            # a numeric query, or Django would try (and fail) to cast a
            # non-numeric string to int for the lookup.
            filters |= Q(student_number=int(query))
        students = Student.objects.filter(institution=institution).filter(filters)

    return render(
        request,
        "enrollment/student_search.html",
        {"search_form": search_form, "students": students},
    )
