"""Formulários Django da app `core`.

The reference-table admin forms below (`Province`, `Municipality`,
`MobileOperator`, `IdentificationDocumentType`, `Profession`) let `code` --
each model's primary key -- be left blank and generated from `name`, instead
of asking whoever is adding a row by hand to invent a slug themselves. See
`apps/core/admin.py` for where these are wired up.
"""

from django import forms
from django.utils.text import slugify

from .models import (
    IdentificationDocumentType,
    MobileOperator,
    Municipality,
    Profession,
    Province,
)


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
