"""View do fluxo de Inscrição (issue #45, RF-MAT-02, docs/06-modulos-e-
funcionalidades.md §6.4)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.core.context import get_current_node_id
from apps.core.view_helpers import first_section_with_errors, require_institution_context

from ..forms import (
    GuardianConsentForm,
    GuardianInscriptionForm,
    GuardianSearchForm,
    StudentInscriptionForm,
)
from ..models import Candidate, Guardian, StudentGuardian
from ..services import DuplicateStudentDocumentError, MissingGuardianConsentError, register_student

# The student half of the wizard (steps 1-3): grouped by topic, not by the
# model's own field order, so "Endereço e Contactos" reads as one step
# instead of an undifferentiated 19-field wall. Steps 4-5 (Encarregado de
# Educação, Consentimento) are each a whole separate Django form, not a
# subset of this one's fields -- see `student_inscription_form.html`.
STUDENT_SECTIONS = [
    {
        "title": "Dados Pessoais",
        "fields": ["first_name", "last_name", "birth_date", "gender", "photo"],
    },
    {
        "title": "Documento",
        "fields": [
            "document_type",
            "document_number",
            "document_issue_date",
            "document_issue_place",
        ],
    },
    {
        "title": "Endereço e Contactos",
        "fields": [
            "province",
            "municipality",
            "district_or_commune",
            "neighborhood",
            "street",
            "house_number",
            "profession",
            "mobile_phone",
            "landline_phone",
            "email",
        ],
    },
]


@login_required
@permission_required("enrollment.add_student", raise_exception=True)
def student_inscription_view(request):
    """Multi-section Inscrição form: Dados Pessoais / Endereço / Contactos
    (via `StudentInscriptionForm`) + Encarregado de Educação (novo ou já
    existente, via search-by-document) + consentimento (issue #143).

    `StudentInscriptionForm` and `GuardianInscriptionForm` share several
    field names (`document_type`, `document_number`, `mobile_phone`, ...) --
    both are rendered inside the same `<form>`, so each uses a distinct
    `prefix` to avoid their POST data colliding.

    Admitting a `Candidate` (issue #42, either from the internal candidate
    list or the public pre-application form, issue #102) lands here with
    `?candidate=<id>`: `Candidate.student_defaults()` pre-fills the form
    instead of fabricating a separate "admission" flow that would just
    duplicate this one. The candidate is only actually marked Admitido once
    the Student is successfully created -- never on the redirect alone, so
    an abandoned form never leaves a candidate wrongly marked as admitted.
    """
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution
    found_guardian = None
    guardian_not_found = False
    candidate_ineligible = False
    candidate_id = request.POST.get("candidate_id") or request.GET.get("candidate")
    candidate = (
        Candidate.objects.filter(
            institution=institution,
            pk=candidate_id,
            status__in=(Candidate.Status.PENDING, Candidate.Status.ACCEPTED),
        ).first()
        if candidate_id
        else None
    )
    if candidate is not None and not candidate.is_eligible_for_admission:
        # Reprovado na prova de aptidão (feedback do utilizador): só quem
        # está apto pode avançar para a Inscrição -- tratado como "nenhum
        # candidato encontrado" (formulário em branco), com um aviso
        # explícito do porquê, em vez de deixar a Secretaria admitir na
        # mesma.
        candidate_ineligible = True
        candidate = None

    if request.method == "POST":
        student_form = StudentInscriptionForm(request.POST, request.FILES, prefix="student")
        consent_form = GuardianConsentForm(request.POST)
        search_form = GuardianSearchForm()
        existing_guardian_id = request.POST.get("existing_guardian_id")

        guardian_form = None
        guardian = None
        if existing_guardian_id:
            guardian = Guardian.objects.filter(
                institution=institution, pk=existing_guardian_id
            ).first()
            found_guardian = guardian
        else:
            guardian_form = GuardianInscriptionForm(request.POST, prefix="guardian")

        forms_valid = student_form.is_valid() and consent_form.is_valid()
        if guardian_form is not None:
            forms_valid = guardian_form.is_valid() and forms_valid
        elif guardian is None:
            # `existing_guardian_id` was posted but no longer resolves to a
            # real Guardian at this institution -- fail closed.
            forms_valid = False

        if forms_valid:
            origin_node_id = get_current_node_id()
            if guardian_form is not None:
                guardian = guardian_form.save(commit=False)
                guardian.institution = institution
                guardian.origin_node_id = origin_node_id
                guardian.save()

            try:
                student = register_student(
                    institution=institution,
                    origin_node_id=origin_node_id,
                    guardian_consent_given_by=guardian,
                    admitted_from_candidate=candidate,
                    **student_form.cleaned_data,
                )
            except DuplicateStudentDocumentError as error:
                student_form.add_error("document_number", str(error))
            except MissingGuardianConsentError as error:
                consent_form.add_error("guardian_consent_given", str(error))
            else:
                StudentGuardian.objects.create(
                    institution=institution,
                    origin_node_id=origin_node_id,
                    student=student,
                    guardian=guardian,
                    is_primary=True,
                    financially_responsible=True,
                )
                if candidate is not None:
                    candidate.status = Candidate.Status.ADMITTED
                    candidate.save(update_fields=["status"])
                return render(
                    request, "enrollment/student_inscription_success.html", {"student": student}
                )
    else:
        student_form = StudentInscriptionForm(
            prefix="student", initial=candidate.student_defaults() if candidate else None
        )
        consent_form = GuardianConsentForm()
        search_form = GuardianSearchForm(request.GET or None)
        if search_form.is_valid() and search_form.cleaned_data["document_number"]:
            found_guardian = Guardian.objects.filter(
                institution=institution,
                document_number=search_form.cleaned_data["document_number"],
            ).first()
            guardian_not_found = found_guardian is None
        guardian_form = None if found_guardian else GuardianInscriptionForm(prefix="guardian")

    if student_form.errors:
        initial_step = first_section_with_errors(student_form, STUDENT_SECTIONS)
    elif guardian_form is not None and guardian_form.errors:
        initial_step = 4
    elif consent_form.errors:
        initial_step = 5
    else:
        initial_step = 1

    return render(
        request,
        "enrollment/student_inscription_form.html",
        {
            "student_form": student_form,
            "guardian_form": guardian_form,
            "search_form": search_form,
            "consent_form": consent_form,
            "found_guardian": found_guardian,
            "guardian_not_found": guardian_not_found,
            "candidate": candidate,
            "candidate_ineligible": candidate_ineligible,
            "student_sections": STUDENT_SECTIONS,
            "initial_step": initial_step,
        },
    )
