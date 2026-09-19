"""Histórico do aluno (issues #49/#50/#51): todas as suas matrículas,
preservadas mesmo depois de anuladas/transferidas, com as acções de
anular e transferir a partir da matrícula actualmente activa."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.context import get_current_node_id

from ..forms import TransferForm
from ..models import Enrollment, Student
from ..services import (
    MatriculaJaEncerradaError,
    MotivoAnulacaoObrigatorioError,
    SchoolClassFullError,
    anular_matricula,
    transferir_aluno,
)

_ACTIVE_STATUSES = [Enrollment.Status.PENDING, Enrollment.Status.ACTIVE]


@login_required
@permission_required("enrollment.change_enrollment", raise_exception=True)
def student_detail_view(request, student_id):
    institution = request.user.institution
    student = get_object_or_404(Student, pk=student_id, institution=institution)

    enrollments = (
        Enrollment.objects.filter(institution=institution, student=student)
        .select_related("school_class", "course", "academic_year", "previous_enrollment")
        .order_by("-academic_year__start_date", "-enrollment_number")
    )
    current_enrollment = next((e for e in enrollments if e.status in _ACTIVE_STATUSES), None)

    transfer_form = None
    if current_enrollment is not None:
        transfer_form = TransferForm(
            institution=institution, current_school_class=current_enrollment.school_class
        )

    if request.method == "POST" and current_enrollment is not None:
        action = request.POST.get("action")
        if action == "anular":
            try:
                anular_matricula(
                    enrollment=current_enrollment,
                    reason=request.POST.get("reason", ""),
                    cancelled_by=request.user,
                )
            except MotivoAnulacaoObrigatorioError as error:
                messages.error(request, str(error))
            except MatriculaJaEncerradaError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Matrícula anulada.")
            return redirect("enrollment:student_detail", student_id=student.id)

        if action == "transferir":
            transfer_form = TransferForm(
                request.POST,
                institution=institution,
                current_school_class=current_enrollment.school_class,
            )
            if transfer_form.is_valid():
                try:
                    transferir_aluno(
                        enrollment=current_enrollment,
                        school_class=transfer_form.cleaned_data["school_class"],
                        transferred_by=request.user,
                        origin_node_id=get_current_node_id(),
                    )
                except (SchoolClassFullError, MatriculaJaEncerradaError) as error:
                    messages.error(request, str(error))
                else:
                    messages.success(request, "Aluno transferido com sucesso.")
                return redirect("enrollment:student_detail", student_id=student.id)

    return render(
        request,
        "enrollment/student_detail.html",
        {
            "student": student,
            "enrollments": enrollments,
            "current_enrollment": current_enrollment,
            "transfer_form": transfer_form,
        },
    )
