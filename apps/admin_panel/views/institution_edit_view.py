"""Edição dos dados da instituição (issue #114, RF-INST-01)."""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.shortcuts import redirect, render

from apps.core.forms import InstitutionEditForm
from apps.core.view_helpers import first_section_with_errors, require_institution_context

SECTIONS = [
    {
        "title": "Identificação",
        "fields": ["name", "tax_id", "ministry_of_education_code", "description"],
    },
    {
        "title": "Morada",
        "fields": [
            "province",
            "municipality",
            "district_or_commune",
            "neighborhood",
            "street",
            "house_number",
        ],
    },
    {
        "title": "Contactos",
        "fields": [
            "landline_phone",
            "unitel_phone",
            "movicel_phone",
            "africell_phone",
            "email",
            "website",
        ],
    },
    {"title": "Identidade visual", "fields": ["logo"]},
    {
        "title": "Documentos oficiais",
        "fields": ["document_header_text", "document_legal_footer_text"],
    },
    {"title": "Admissões", "fields": ["admission_exam_passing_score"]},
]


@login_required
@permission_required("core.change_institution", raise_exception=True)
def institution_edit_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    if request.method == "POST":
        form = InstitutionEditForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            form.save()
            success(request, "Dados da instituição actualizados.")
            return redirect("admin_panel:institution_edit")
    else:
        form = InstitutionEditForm(instance=institution)

    return render(
        request,
        "admin_panel/institution_edit.html",
        {
            "form": form,
            "sections": SECTIONS,
            "initial_step": first_section_with_errors(form, SECTIONS),
        },
    )
