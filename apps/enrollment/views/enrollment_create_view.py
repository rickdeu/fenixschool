"""View do fluxo de Matrícula (issue #47, RF-MAT-05/06/07, docs/06-modulos-e-
funcionalidades.md §6.4)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.core.context import get_current_node_id
from apps.core.view_helpers import require_institution_context

from ..forms import EnrollmentForm
from ..models import Student
from ..services import (
    SchoolClassFullError,
    StudentAlreadyEnrolledError,
    emitir_comprovativo_matricula,
    enroll_student,
)


@login_required
@permission_required("enrollment.add_enrollment", raise_exception=True)
def enrollment_create_view(request, student_id):
    """ "Inscrições → Matrículas → Nova Matrícula", continued: the student's
    data is pre-loaded (RF-MAT-04's search already found them) and the
    Secretaria only picks the Turma, presented document and observations.

    "Guardar e Imprimir" (RF-MAT-06, docs/06-modulos-e-funcionalidades.md
    §6.4's own step 7: "Guardar e Imprimir grava a matrícula e emite
    comprovativo em PDF") is a single action, not two: on success this
    returns the comprovativo PDF directly, generated automatically, never
    a separate opt-in step.
    """
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    student = get_object_or_404(Student, pk=student_id, institution=institution)
    capacity_warning = None

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
                    force=request.POST.get("force") == "1",
                    course=school_class.course,
                    academic_year=school_class.academic_year,
                    cycle=school_class.course.cycle,
                    curricular_year=school_class.curricular_year,
                    **fields,
                )
            except SchoolClassFullError as error:
                # Aviso, não bloqueio (issue #174/RF-MAT-07): o formulário
                # (já bound, com a turma escolhida) volta a aparecer com um
                # botão "confirmar mesmo assim" que resubmete a mesma
                # escolha com force=1, em vez de recusar a matrícula.
                capacity_warning = str(error)
            except StudentAlreadyEnrolledError as error:
                form.add_error("school_class", str(error))
            else:
                _issued, pdf = emitir_comprovativo_matricula(
                    enrollment=enrollment,
                    issued_by=request.user,
                    origin_node_id=get_current_node_id(),
                )
                return HttpResponse(pdf, content_type="application/pdf")
    else:
        form = EnrollmentForm(institution=institution, student=student)

    return render(
        request,
        "enrollment/enrollment_form.html",
        {"form": form, "student": student, "capacity_warning": capacity_warning},
    )
