"""Formulários Django da app `public_site`."""

from django import forms

from apps.academic.models import Course
from apps.enrollment.models import Candidate


class PreApplicationForm(forms.ModelForm):
    """Pré-candidatura pública (issue #102, RF-PUB-03) -- cria um `Candidato`
    (`apps.enrollment`) directamente a partir do portal público, sem
    autenticação. `institution` restringe `desired_course` às ofertas reais
    desta instituição, tal como `home_view` já faz para a lista de cursos."""

    class Meta:
        model = Candidate
        fields = [
            "full_name",
            "birth_date",
            "document_type",
            "document_number",
            "document_expiry_date",
            "desired_course",
            "contact",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "document_expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, institution, **kwargs):
        super().__init__(*args, **kwargs)
        self.institution = institution
        self.fields["desired_course"].queryset = Course.all_objects.for_institution(
            institution.id
        ).order_by("name")

    def clean_document_number(self):
        # Feedback do utilizador: "um user não pode fazer várias
        # candidaturas" -- bloqueia só candidaturas ainda em curso; uma
        # rejeitada anteriormente não impede reaplicar (sem `tenant_context`
        # activo aqui, é `all_objects` explícito, não `objects`).
        document_number = self.cleaned_data["document_number"]
        already_applied = (
            Candidate.all_objects.filter(
                institution=self.institution,
                document_number=document_number,
            )
            .exclude(status=Candidate.Status.REJECTED)
            .exists()
        )
        if already_applied:
            raise forms.ValidationError(
                "Já existe uma candidatura em curso com este número de documento. "
                "Contacte a secretaria se precisar de a corrigir."
            )
        return document_number


class ApplicationReceiptLookupForm(forms.Form):
    """ "Voltar a emitir [o comprovativo] quando necessário" (issue #102,
    feedback do utilizador) -- self-service público sem autenticação, só
    pelo número de documento apresentado na candidatura."""

    document_number = forms.CharField(label="Número do documento", max_length=50)

    def __init__(self, *args, institution, **kwargs):
        super().__init__(*args, **kwargs)
        self.institution = institution

    def clean_document_number(self):
        return self.cleaned_data["document_number"].strip()

    def clean(self):
        cleaned_data = super().clean()
        document_number = cleaned_data.get("document_number")
        if not document_number:
            return cleaned_data

        candidate = (
            Candidate.all_objects.filter(
                institution=self.institution, document_number=document_number
            )
            .order_by("-application_date")
            .first()
        )
        if candidate is None:
            raise forms.ValidationError(
                "Não encontrámos nenhuma candidatura com este número de documento."
            )
        cleaned_data["candidate"] = candidate
        return cleaned_data
