"""Formulários Django da app `core`.

The reference-table admin forms below (`Province`, `Municipality`,
`MobileOperator`, `IdentificationDocumentType`, `Profession`) let `code` --
each model's primary key -- be left blank and generated from `name`, instead
of asking whoever is adding a row by hand to invent a slug themselves. See
`apps/core/admin.py` for where these are wired up.
"""

from django import forms
from django.contrib.auth import password_validation
from django.utils.text import slugify

from apps.accounts.models import User

from .models import (
    AcademicCycle,
    AcademicTerm,
    AcademicYear,
    IdentificationDocumentType,
    Institution,
    MobileOperator,
    Municipality,
    NonTeachingDay,
    Profession,
    Province,
)
from .widgets import MunicipalitySelect


class SlugFromNameFormMixin(forms.ModelForm):
    """Auto-generates the `code` primary key from `name` when left blank.

    Also re-slugifies a `code` typed in by hand, so a stray space or an
    uppercase letter can't create a row whose primary key doesn't match this
    app's slug convention (the one `scripts/generate_core_reference_fixtures.py`
    uses for the fixtures).
    """

    code = forms.CharField(
        max_length=100,
        required=False,
        help_text="Deixe em branco para gerar automaticamente a partir do nome.",
    )

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if name:
            cleaned_data["code"] = slugify(cleaned_data.get("code") or name)
        return cleaned_data


class ProvinceAdminForm(SlugFromNameFormMixin):
    class Meta:
        model = Province
        fields = ("code", "name")


class MobileOperatorAdminForm(SlugFromNameFormMixin):
    class Meta:
        model = MobileOperator
        fields = ("code", "name")


class IdentificationDocumentTypeAdminForm(SlugFromNameFormMixin):
    class Meta:
        model = IdentificationDocumentType
        fields = ("code", "name")


class ProfessionAdminForm(SlugFromNameFormMixin):
    class Meta:
        model = Profession
        fields = ("code", "name")


class MunicipalityAdminForm(SlugFromNameFormMixin):
    """Same as `SlugFromNameFormMixin`, but the generated code is prefixed
    with the parent province's own code (e.g. "huila-lubango"), matching the
    fixtures -- a bare municipality name is not unique nationwide.
    """

    class Meta:
        model = Municipality
        fields = ("code", "name", "province")

    def clean(self):
        cleaned_data = super().clean()
        # When used as `ProvinceAdmin`'s inline, `province` is the parent
        # link: the formset sets it straight on `self.instance` and excludes
        # it from this form's own fields/`cleaned_data`.
        province = cleaned_data.get("province") or getattr(self.instance, "province", None)
        name = cleaned_data.get("name")
        if province and name:
            cleaned_data["code"] = f"{province.code}-{slugify(name)}"
        return cleaned_data


class InstitutionSetupForm(forms.ModelForm):
    """The Institution half of the setup wizard (issue #17)."""

    class Meta:
        model = Institution
        fields = [
            "name",
            "tax_id",
            "ministry_of_education_code",
            "province",
            "municipality",
            "email",
            "website",
        ]
        widgets = {"municipality": MunicipalitySelect}


class ManagerSetupForm(forms.ModelForm):
    """The Manager (Institution Administrator) half of the setup wizard (issue #17)."""

    password = forms.CharField(widget=forms.PasswordInput, label="Palavra-passe")
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput, label="Confirmar palavra-passe"
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone"]

    def clean_password(self):
        password = self.cleaned_data["password"]
        # Uses AUTH_PASSWORD_VALIDATORS (config/settings/base.py) -- this is
        # the very first password the system ever stores, so it goes through
        # the same policy as every later one.
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirmation", "As palavras-passe não coincidem.")
        return cleaned_data


class NonTeachingDayForm(forms.ModelForm):
    """Dia não lectivo -- feriado ou outro dia sem aulas (issue #20, RF-INST-07)."""

    class Meta:
        model = NonTeachingDay
        fields = ["date", "description", "scope"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class InstitutionEditForm(forms.ModelForm):
    """Dados editáveis da instituição a partir do ecrã dedicado (issue #114,
    RF-INST-01) -- exclui `default_grading_formula` (tem o seu próprio ecrã,
    issue #18) e `blocks_documents_with_outstanding_debt` (RF-FIN-06, sem
    nenhuma funcionalidade financeira real ainda por parametrizar)."""

    class Meta:
        model = Institution
        fields = [
            "name",
            "tax_id",
            "ministry_of_education_code",
            "description",
            "province",
            "municipality",
            "district_or_commune",
            "neighborhood",
            "street",
            "house_number",
            "landline_phone",
            "unitel_phone",
            "movicel_phone",
            "africell_phone",
            "email",
            "website",
            "logo",
        ]
        widgets = {"municipality": MunicipalitySelect}


class AcademicYearForm(forms.ModelForm):
    """Ano lectivo (issue #16, RF-INST-03)."""

    class Meta:
        model = AcademicYear
        fields = ["designation", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AcademicTermForm(forms.ModelForm):
    """Período lectivo dentro de um ano lectivo (issue #16, RF-INST-04)."""

    class Meta:
        model = AcademicTerm
        fields = ["number", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AcademicCycleForm(forms.ModelForm):
    """Ciclo lectivo (issue #16, RF-INST-05)."""

    class Meta:
        model = AcademicCycle
        fields = ["designation", "order"]
