"""Tests for the `core.Institution` model (see apps/core/models/institution.py)."""

import pytest
from django.db.models import ProtectedError

from apps.core.models import Institution, Municipality, Province

pytestmark = pytest.mark.django_db


def test_str_returns_the_institution_name(institution_factory):
    institution = institution_factory("Escola Piloto")

    assert str(institution) == "Escola Piloto"


def test_optional_fields_default_to_blank_without_requiring_a_value(institution_factory):
    institution = institution_factory("Escola Piloto")

    assert institution.tax_id == ""
    assert institution.ministry_of_education_code == ""
    assert institution.province is None
    assert institution.municipality is None
    assert institution.email == ""
    assert institution.website == ""
    assert not institution.logo
    assert institution.default_grading_formula == {}
    assert institution.blocks_documents_with_outstanding_debt is False


def test_full_administrative_and_contact_data_can_be_set():
    province = Province.objects.create(code="test-province", name="Test Province")
    municipality = Municipality.objects.create(
        code="test-province-test-municipality", name="Test Municipality", province=province
    )

    institution = Institution.objects.create(
        name="Escola Piloto",
        tax_id="5000000000",
        ministry_of_education_code="MED-001",
        province=province,
        municipality=municipality,
        district_or_commune="Ingombota",
        neighborhood="Maianga",
        street="Rua Amílcar Cabral",
        house_number="123",
        landline_phone="222000000",
        unitel_phone="923000000",
        movicel_phone="913000000",
        africell_phone="991000000",
        email="secretaria@escolapiloto.co.ao",
        website="https://escolapiloto.co.ao",
        default_grading_formula={"formula": "media_aritmetica_simples"},
        blocks_documents_with_outstanding_debt=True,
    )

    institution.refresh_from_db()
    assert institution.province == province
    assert institution.municipality == municipality
    assert institution.default_grading_formula == {"formula": "media_aritmetica_simples"}
    assert institution.blocks_documents_with_outstanding_debt is True


def test_deleting_a_province_still_in_use_by_an_institution_is_protected(institution_factory):
    province = Province.objects.create(code="test-province", name="Test Province")
    institution = institution_factory("Escola Piloto")
    institution.province = province
    institution.save()

    with pytest.raises(ProtectedError):
        province.delete()
