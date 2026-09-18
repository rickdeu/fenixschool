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
        fields = ["full_name", "birth_date", "desired_course", "contact"]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, institution, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["desired_course"].queryset = Course.all_objects.for_institution(
            institution.id
        ).order_by("name")
