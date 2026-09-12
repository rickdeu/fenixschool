"""Tests for the `core` reference tables' custom admin forms (apps/core/forms.py).

`ProvinceAdmin` exposes municipalities as an inline (`MunicipalityInline`), and
every reference-table admin form auto-generates the `code` primary key from
`name` when left blank, instead of asking whoever is adding a row by hand to
invent a slug themselves.
"""

import pytest

from apps.core.admin import ProvinceAdmin
from apps.core.forms import (
    MobileOperatorAdminForm,
    MunicipalityAdminForm,
    ProvinceAdminForm,
)
from apps.core.models import Municipality, Province

pytestmark = pytest.mark.django_db


def test_blank_code_is_generated_from_name():
    form = ProvinceAdminForm(data={"name": "Nova Província"})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["code"] == "nova-provincia"


def test_a_hand_typed_code_is_still_normalized():
    form = MobileOperatorAdminForm(data={"name": "Nova Operadora", "code": "Nova Operadora!"})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["code"] == "nova-operadora"


def test_municipality_code_is_prefixed_with_its_provinces_code():
    luanda = Province.objects.get(code="luanda")

    form = MunicipalityAdminForm(data={"name": "Bairro Novo", "province": luanda.pk})

    assert form.is_valid(), form.errors
    assert form.cleaned_data["code"] == "luanda-bairro-novo"


def test_province_admin_list_display_shows_municipality_count():
    luanda = Province.objects.get(code="luanda")
    admin = ProvinceAdmin(Province, admin_site=None)

    assert admin.municipality_count(luanda) == luanda.municipalities.count() > 0


def test_municipality_code_still_generates_when_province_only_on_the_instance():
    """Mirrors `ProvinceAdmin`'s inline: the formset sets `province` straight
    on the unsaved instance, and the hidden inline field also carries it, but
    this exercises the fallback to `self.instance.province` directly."""
    luanda = Province.objects.get(code="luanda")
    instance = Municipality(province=luanda)

    form = MunicipalityAdminForm(
        data={"name": "Bairro Novo", "province": luanda.pk}, instance=instance
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["code"] == "luanda-bairro-novo"
