"""Tests for the national reference tables (issue #11, RNF-LOC-05).

These rows are not created by any test fixture: they come from the
`core.0002_reference_data` migration itself, which every test database goes
through when it is built (see docs/13-testes-e-qualidade.md). So these tests
exercise the exact same data an operator gets from a plain `migrate`.
"""

import pytest
from django.core.management import call_command

from apps.core.models import (
    IdentificationDocumentType,
    MobileOperator,
    Municipality,
    Profession,
    Province,
)

pytestmark = pytest.mark.django_db


def test_migrate_preloads_the_21_current_angolan_provinces():
    assert Province.objects.count() == 21
    assert Province.objects.filter(code="luanda", name="Luanda").exists()
    # Provinces created by the 2024 reform (Lei 14/24), not just the old 18.
    assert Province.objects.filter(code="icolo-e-bengo").exists()
    assert Province.objects.filter(code="cuando").exists()
    assert Province.objects.filter(code="cubango").exists()
    assert Province.objects.filter(code="moxico-leste").exists()


def test_every_municipality_belongs_to_a_province():
    assert Municipality.objects.count() > 0
    assert not Municipality.objects.filter(province__isnull=True).exists()


def test_municipalities_are_scoped_to_their_own_province():
    luanda_municipalities = set(
        Municipality.objects.filter(province_id="luanda").values_list("name", flat=True)
    )
    icolo_e_bengo_municipalities = set(
        Municipality.objects.filter(province_id="icolo-e-bengo").values_list("name", flat=True)
    )

    assert "Viana" in luanda_municipalities
    assert "Catete" in icolo_e_bengo_municipalities
    assert luanda_municipalities.isdisjoint(icolo_e_bengo_municipalities)


def test_migrate_preloads_the_three_mobile_operators():
    names = set(MobileOperator.objects.values_list("name", flat=True))

    assert names == {"Unitel", "Movicel", "Africell"}


def test_migrate_preloads_the_four_identification_document_types():
    names = set(IdentificationDocumentType.objects.values_list("name", flat=True))

    assert names == {
        "Bilhete de Identidade",
        "Cédula Pessoal",
        "Passaporte",
        "Assento de Nascimento",
    }


def test_migrate_preloads_a_list_of_professions():
    assert Profession.objects.count() > 0
    assert Profession.objects.filter(code="professor-a").exists()


def test_str_methods_are_human_readable():
    province = Province.objects.get(code="luanda")
    municipality = Municipality.objects.get(code="luanda-viana")
    operator = MobileOperator.objects.get(code="unitel")

    assert str(province) == "Luanda"
    assert str(municipality) == "Viana (Luanda)"
    assert str(operator) == "Unitel"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "provinces_municipalities",
        "mobile_operators",
        "document_types",
        "professions",
    ],
)
def test_each_fixture_is_loadable_on_its_own_via_loaddata(fixture_name):
    """Acceptance criterion: "4 fixtures criadas e carregáveis via `loaddata`"."""
    call_command("loaddata", fixture_name, app_label="core")


def test_fixture_field_values_pass_model_validation():
    """Guards against a value too long for its field's `max_length` (e.g. a
    21-character document type code against a 20-character field): SQLite,
    used by every other test in this file, never enforces `CharField`
    `max_length` at the database level, so such a value passes `migrate`
    here yet fails against real PostgreSQL with
    `DataError: value too long for type character varying(N)`.
    `full_clean()` checks it in Python instead, independent of backend.
    """
    for model in (Province, Municipality, MobileOperator, IdentificationDocumentType, Profession):
        for obj in model.objects.all():
            obj.full_clean()
