"""Formulários Django da app `enrollment` -- fluxos de Inscrição (issue #45) e
Matrícula (issue #47)."""

from django import forms

from apps.academic.models import SchoolClass
from apps.core.widgets import MunicipalitySelect

from .models import Enrollment, Guardian, Student


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
            "municipality": MunicipalitySelect,
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
        widgets = {"municipality": MunicipalitySelect}


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


class StudentSearchForm(forms.Form):
    """Localizar um aluno já inscrito, para efeitos de matrícula (RF-MAT-04)."""

    q = forms.CharField(label="Nº de aluno, documento ou nome", required=False)


class EnrollmentForm(forms.ModelForm):
    """Dados da Matrícula (RF-MAT-05).

    `course`/`academic_year`/`cycle`/`curricular_year` are deliberately not
    fields here: they are derived from the chosen `school_class` (a Turma
    already fixes its own course/year/cycle -- see
    `apps/academic/models/school_class_model.py`), so the Secretaria only
    ever has to pick one thing that can't disagree with itself, instead of
    four separate dropdowns that could be set to an inconsistent combination.
    """

    class Meta:
        model = Enrollment
        fields = [
            "school_class",
            "presented_document_type",
            "presented_document_number",
            "document_issue_date",
            "document_issue_place",
            "notes",
            "is_repeating",
            "previous_enrollment",
        ]
        widgets = {"document_issue_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, institution=None, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if institution is not None:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                institution=institution
            )
        self.fields["previous_enrollment"].required = False
        if student is not None:
            self.fields["previous_enrollment"].queryset = Enrollment.objects.filter(student=student)
