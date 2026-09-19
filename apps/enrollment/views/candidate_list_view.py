"""Lista de candidatos, com admissão para a Inscrição (issue #42, RF-MAT-10)
-- inclui os que chegaram pela pré-candidatura pública (issue #102), a
prova de aptidão (nota + apto/não apto) e a convocação para segunda
chamada, quando pedidas pelo utilizador."""

from decimal import InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.academic.models import Course, SchoolClass
from apps.core.models import AcademicYear
from apps.core.view_helpers import require_institution_context

from ..models import Candidate
from ..services import (
    CandidateAlreadyDecidedError,
    CandidateAlreadyEligibleError,
    ExamScoreOutOfRangeError,
    aceitar_candidatos_em_lote,
    convocar_para_segunda_chamada,
    registar_nota_candidato,
)


def _vacancy_info(institution, course):
    """Só informativo (mostrado junto de cada curso para apoiar a decisão
    de convocar ou não uma segunda chamada) -- nunca decide nada sozinho:
    contar vagas "a sério" exigiria já saber em que Turma cada candidato
    vai cair, o que só a própria Matrícula decide, não a Candidatura."""
    latest_year = (
        AcademicYear.objects.filter(institution=institution).order_by("-start_date").first()
    )
    if latest_year is None:
        return None
    school_classes = SchoolClass.objects.filter(
        institution=institution, course=course, academic_year=latest_year
    )
    capacity = sum(sc.max_enrollment for sc in school_classes)
    occupied = sum(sc.active_enrollment_count() for sc in school_classes)
    return {
        "academic_year": latest_year,
        "capacity": capacity,
        "occupied": occupied,
        "remaining": capacity - occupied,
    }


@login_required
@permission_required("enrollment.view_candidate", raise_exception=True)
def candidate_list_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "admitir_lote":
            count = aceitar_candidatos_em_lote(
                institution=institution, candidate_ids=request.POST.getlist("candidate_ids")
            )
            if count:
                messages.success(request, f"{count} candidato(s) aceite(s).")
            else:
                messages.error(
                    request, "Nenhum candidato seleccionado estava apto para ser aceite."
                )
            return redirect("enrollment:candidate_list")

        candidate = get_object_or_404(
            Candidate, institution=institution, pk=request.POST.get("candidate_id")
        )
        if action == "registar_nota":
            score = request.POST.get("score", "").strip()
            try:
                registar_nota_candidato(candidate=candidate, score=score)
            except (InvalidOperation, TypeError):
                messages.error(request, "Indique uma nota válida (0-20).")
            except (ExamScoreOutOfRangeError, CandidateAlreadyDecidedError) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Nota registada.")
        elif action == "segunda_chamada":
            try:
                convocar_para_segunda_chamada(candidate=candidate)
            except (CandidateAlreadyDecidedError, CandidateAlreadyEligibleError) as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Candidato convocado para segunda chamada.")
        return redirect("enrollment:candidate_list")

    courses = Course.objects.filter(institution=institution).order_by("name")
    selected_course_id = request.GET.get("curso") or ""
    selected_status = request.GET.get("estado") or ""
    query = request.GET.get("q", "").strip()

    candidates_qs = Candidate.objects.filter(
        institution=institution,
        status__in=[
            Candidate.Status.PENDING,
            Candidate.Status.SECOND_CALL,
            Candidate.Status.ACCEPTED,
        ],
    )
    if selected_course_id:
        candidates_qs = candidates_qs.filter(desired_course_id=selected_course_id)
    if selected_status:
        candidates_qs = candidates_qs.filter(status=selected_status)
    if query:
        candidates_qs = candidates_qs.filter(
            Q(full_name__icontains=query) | Q(document_number__icontains=query)
        )

    candidates = list(
        candidates_qs.select_related("document_type", "desired_course").order_by(
            "-application_date"
        )
    )
    vacancy_by_course_id = {
        course.id: _vacancy_info(institution, course)
        for course in {c.desired_course for c in candidates}
    }
    for candidate in candidates:
        # Anexado directamente ao objecto (em vez de um dict à parte
        # indexado por curso): o template não tem forma nativa de indexar
        # um dict por uma variável.
        candidate.vacancy_info = vacancy_by_course_id[candidate.desired_course_id]

    return render(
        request,
        "enrollment/candidate_list.html",
        {
            "candidates": candidates,
            "courses": courses,
            "selected_course_id": selected_course_id,
            "status_choices": [
                (Candidate.Status.PENDING, Candidate.Status.PENDING.label),
                (Candidate.Status.SECOND_CALL, Candidate.Status.SECOND_CALL.label),
                (Candidate.Status.ACCEPTED, Candidate.Status.ACCEPTED.label),
            ],
            "selected_status": selected_status,
            "query": query,
        },
    )
