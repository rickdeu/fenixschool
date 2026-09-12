"""Tests for the minimal `core.Institution` model (see apps/core/models/institution.py)."""

import pytest

pytestmark = pytest.mark.django_db


def test_str_returns_the_institution_name(institution_factory):
    institution = institution_factory("Escola Piloto")

    assert str(institution) == "Escola Piloto"
