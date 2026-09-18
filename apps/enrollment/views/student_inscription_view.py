"""View do fluxo de Inscrição (issue #45, RF-MAT-02, docs/06-modulos-e-
funcionalidades.md §6.4)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.core.context import get_current_node_id

from ..forms import (
    GuardianConsentForm,
    GuardianInscriptionForm,
    GuardianSearchForm,
    StudentInscriptionForm,
)
from ..models import Guardian, StudentGuardian
from ..services import DuplicateStudentDocumentError, MissingGuardianConsentError, register_student


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
    """
    institution = request.institution
    found_guardian = None
    guardian_not_found = False

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
                return render(
                    request, "enrollment/student_inscription_success.html", {"student": student}
                )
    else:
        student_form = StudentInscriptionForm(prefix="student")
        consent_form = GuardianConsentForm()
        search_form = GuardianSearchForm(request.GET or None)
        if search_form.is_valid() and search_form.cleaned_data["document_number"]:
            found_guardian = Guardian.objects.filter(
                institution=institution,
                document_number=search_form.cleaned_data["document_number"],
            ).first()
            guardian_not_found = found_guardian is None
        guardian_form = None if found_guardian else GuardianInscriptionForm(prefix="guardian")

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
        },
    )
