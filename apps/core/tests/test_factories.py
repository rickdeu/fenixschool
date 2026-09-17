"""Tests for `apps/core/factories.py` (issue #153)."""

import pytest

from apps.core.factories import (
    IdentificationDocumentTypeFactory,
    InstitutionFactory,
    MobileOperatorFactory,
    MunicipalityFactory,
    ProfessionFactory,
    ProvinceFactory,
)

pytestmark = pytest.mark.django_db


def test_institution_factory_creates_a_persisted_institution():
    institution = InstitutionFactory()

    assert institution.pk is not None
    assert institution.name


def test_institution_factory_sequence_produces_distinct_names():
    first = InstitutionFactory()
    second = InstitutionFactory()

    assert first.name != second.name


def test_municipality_factory_creates_its_province_via_subfactory():
    municipality = MunicipalityFactory()

    assert municipality.province.pk is not None


def test_reference_data_factories_create_persisted_rows():
    assert ProvinceFactory().pk is not None
    assert MobileOperatorFactory().pk is not None
    assert IdentificationDocumentTypeFactory().pk is not None
    assert ProfessionFactory().pk is not None
