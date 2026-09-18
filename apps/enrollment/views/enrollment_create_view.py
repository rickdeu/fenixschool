"""View do fluxo de Matrícula (issue #47, RF-MAT-05/06/07, docs/06-modulos-e-
funcionalidades.md §6.4)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from apps.core.context import get_current_node_id

from ..forms import EnrollmentForm
from ..models import Student
from ..services import SchoolClassFullError, enroll_student


@login_required
@permission_required("enrollment.add_enrollment", raise_exception=True)
def enrollment_create_view(request, student_id):
    """ "Inscrições → Matrículas → Nova Matrícula", continued: the student's
    data is pre-loaded (RF-MAT-04's search already found them) and the
    Secretaria only picks the Turma, presented document and observations.

    "Guardar e Imprimir" (RF-MAT-06 -- a printable PDF proof) is only
    "Guardar" here: PDF generation is its own dedicated task (`reports`),
    not fabricated in this view -- the success page says so plainly instead
    of pretending to offer a download that doesn't exist.
    """
    institution = request.institution
    student = get_object_or_404(Student, pk=student_id, institution=institution)

    if request.method == "POST":
        form = EnrollmentForm(request.POST, institution=institution, student=student)
        if form.is_valid():
            fields = dict(form.cleaned_data)
            school_class = fields.pop("school_class")

            try:
                enrollment = enroll_student(
                    institution=institution,
                    student=student,
                    school_class=school_class,
                    origin_node_id=get_current_node_id(),
                    course=school_class.course,
                    academic_year=school_class.academic_year,
                    cycle=school_class.course.cycle,
                    curricular_year=school_class.curricular_year,
                    **fields,
                )
            except SchoolClassFullError as error:
                form.add_error("school_class", str(error))
            else:
                return render(
                    request, "enrollment/enrollment_success.html", {"enrollment": enrollment}
                )
    else:
        form = EnrollmentForm(institution=institution, student=student)

    return render(request, "enrollment/enrollment_form.html", {"form": form, "student": student})
