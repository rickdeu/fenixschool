"""Matrícula em lote de alunos admitidos a partir de candidaturas (RF-MAT-07),
continuação directa do fluxo de admissão de Candidatos (issue #42): em vez de
repetir a Matrícula uma a uma em Alunos → Matrículas para cada aluno inscrito
a partir de uma candidatura, a Secretaria escolhe um curso e uma turma e
matricula de uma só vez todos os que ainda não têm nenhuma matrícula --
os dados do "documento apresentado" são copiados do próprio Aluno (o mesmo
documento já registado na Inscrição), nunca inventados.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.shortcuts import render

from apps.academic.models import Course, SchoolClass
from apps.core.context import get_current_node_id
from apps.core.view_helpers import require_institution_context

from ..models import Student
from ..services import SchoolClassFullError, enroll_student


def _eligible_students(institution, course):
    return Student.objects.filter(
        institution=institution,
        admitted_from_candidate__isnull=False,
        admitted_from_candidate__desired_course=course,
        enrollments__isnull=True,
    ).order_by("first_name", "last_name")


@login_required
@permission_required("enrollment.add_enrollment", raise_exception=True)
def bulk_enrollment_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    courses = Course.objects.filter(institution=institution).order_by("name")

    course_id = request.POST.get("course") or request.GET.get("course")
    course = (
        Course.objects.filter(institution=institution, pk=course_id).first() if course_id else None
    )

    school_classes = SchoolClass.objects.none()
    eligible_students = Student.objects.none()
    if course is not None:
        school_classes = SchoolClass.objects.filter(institution=institution, course=course)
        eligible_students = _eligible_students(institution, course)

    if request.method == "POST" and course is not None:
        school_class_id = request.POST.get("school_class")
        school_class = (
            school_classes.filter(pk=school_class_id).first() if school_class_id else None
        )
        selected_ids = request.POST.getlist("student_ids")

        if school_class is None:
            messages.error(request, "Escolha uma turma.")
        elif not selected_ids:
            messages.error(request, "Escolha pelo menos um aluno.")
        else:
            origin_node_id = get_current_node_id()
            enrolled_count = 0
            for student in eligible_students.filter(pk__in=selected_ids):
                try:
                    enroll_student(
                        institution=institution,
                        student=student,
                        school_class=school_class,
                        origin_node_id=origin_node_id,
                        course=school_class.course,
                        academic_year=school_class.academic_year,
                        cycle=school_class.course.cycle,
                        curricular_year=school_class.curricular_year,
                        presented_document_type=student.document_type,
                        presented_document_number=student.document_number,
                        document_issue_date=student.document_issue_date,
                        document_issue_place=student.document_issue_place,
                    )
                except SchoolClassFullError as error:
                    messages.error(request, str(error))
                    break
                else:
                    enrolled_count += 1

            if enrolled_count:
                success(request, f"{enrolled_count} aluno(s) matriculado(s) em {school_class}.")
            eligible_students = _eligible_students(institution, course)

    return render(
        request,
        "enrollment/bulk_enrollment.html",
        {
            "courses": courses,
            "course": course,
            "school_classes": school_classes,
            "eligible_students": eligible_students,
        },
    )
