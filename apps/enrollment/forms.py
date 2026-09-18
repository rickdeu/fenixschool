"""Formulários Django da app `enrollment` -- fluxo de Inscrição (issue #45)."""

from django import forms

from .models import Guardian, Student


class StudentInscriptionForm(forms.ModelForm):
    """Dados do aluno (RF-MAT-02): pessoais, documento, endereço, contactos.

    Excludes every system-managed field (`student_number`,
    `registration_date`, `guardian_consent_given_by`/`_at`, `institution`,
    `origin_node_id`, `status`) -- those are set by the view/service, never
    typed in by the Secretaria.
    """

    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
            "birth_date",
            "gender",
            "photo",
            "document_type",
            "document_number",
            "document_issue_date",
            "document_issue_place",
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
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "document_issue_date": forms.DateInput(attrs={"type": "date"}),
        }


class GuardianSearchForm(forms.Form):
    """Procura de um Encarregado de Educação já existente, por documento."""

    document_number = forms.CharField(label="Nº de documento do Encarregado", required=False)


class GuardianInscriptionForm(forms.ModelForm):
    """Dados de um novo Encarregado de Educação, associado no acto de Inscrição."""

    class Meta:
        model = Guardian
        fields = [
            "full_name",
            "kinship",
            "document_type",
            "document_number",
            "mobile_phone",
            "landline_phone",
            "email",
            "profession",
            "province",
            "municipality",
            "district_or_commune",
            "neighborhood",
            "street",
            "house_number",
        ]


class GuardianConsentForm(forms.Form):
    """Consentimento do Encarregado (issue #143, Lei 22/11, RNF-AUD-02)."""

    guardian_consent_given = forms.BooleanField(
        label=(
            "O Encarregado de Educação identificado acima consente o "
            "tratamento dos dados pessoais do aluno."
        ),
        required=True,
        error_messages={
            "required": (
                "É obrigatório o consentimento do Encarregado de Educação para gravar a inscrição."
            )
        },
    )
