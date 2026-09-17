"""Tests for the academic calendar models (issue #16, docs/05-modelo-de-dados.md §5.3)."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicTerm, AcademicYear, NonTeachingDay

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def test_academic_year_str_is_its_designation(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    assert str(year) == "2026/2027"


def test_academic_year_end_date_must_be_after_start_date(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        with pytest.raises(ValidationError):
            AcademicYear.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                designation="2026/2027",
                start_date=date(2026, 12, 15),
                end_date=date(2026, 2, 1),
            )


def test_only_one_current_academic_year_per_institution_at_model_level(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2025/2026",
            start_date=date(2025, 2, 1),
            end_date=date(2025, 12, 15),
            is_current=False,
        )
        AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )

        with pytest.raises(ValidationError):
            AcademicYear.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                designation="2027/2028",
                start_date=date(2027, 2, 1),
                end_date=date(2027, 12, 15),
                is_current=True,
            )


def test_one_current_academic_year_constraint_is_enforced_at_the_database_level(
    institution_factory,
):
    """The DB constraint itself, bypassing model-level `full_clean()` --
    proves this holds even under concurrent/raw writes, not just through the
    ORM's own `save()`."""
    institution = institution_factory()
    with tenant_context(institution.id):
        AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )

        second = AcademicYear(
            institution=institution,
            origin_node_id=_origin(),
            designation="2027/2028",
            start_date=date(2027, 2, 1),
            end_date=date(2027, 12, 15),
            is_current=True,
        )
        with transaction.atomic(), pytest.raises(IntegrityError):
            # Bypasses `AcademicYear.save()`'s `full_clean()` on purpose.
            AcademicYear.objects.bulk_create([second])


def test_different_institutions_can_each_have_their_own_current_academic_year(
    institution_factory,
):
    school_a = institution_factory("School A")
    school_b = institution_factory("School B")

    with tenant_context(school_a.id):
        AcademicYear.objects.create(
            institution=school_a,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )
    with tenant_context(school_b.id):
        AcademicYear.objects.create(
            institution=school_b,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
            is_current=True,
        )


def test_academic_term_must_fall_within_its_academic_year(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

        # Valid term: entirely inside the academic year.
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

        with pytest.raises(ValidationError):
            AcademicTerm.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                academic_year=year,
                number=2,
                start_date=date(2026, 6, 1),
                # Ends after the academic year itself ends.
                end_date=date(2027, 1, 15),
            )


def test_academic_term_end_date_must_be_after_start_date(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

        with pytest.raises(ValidationError):
            AcademicTerm.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                academic_year=year,
                number=1,
                start_date=date(2026, 5, 31),
                end_date=date(2026, 2, 1),
            )


def test_academic_term_must_belong_to_an_academic_year_of_the_same_institution(
    institution_factory,
):
    school_a = institution_factory("School A")
    school_b = institution_factory("School B")

    with tenant_context(school_a.id):
        year_a = AcademicYear.objects.create(
            institution=school_a,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )

    with tenant_context(school_b.id):
        with pytest.raises(ValidationError):
            AcademicTerm.objects.create(
                institution=school_b,
                origin_node_id=_origin(),
                academic_year=year_a,
                number=1,
                start_date=date(2026, 2, 1),
                end_date=date(2026, 5, 31),
            )


def test_academic_term_numbers_are_unique_within_an_academic_year(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

        # AcademicTerm.save() runs full_clean(), so validate_unique() catches
        # this as a ValidationError before it ever reaches the database --
        # unlike the DB-level-only check in the next test.
        with pytest.raises(ValidationError):
            AcademicTerm.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                academic_year=year,
                number=1,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 9, 30),
            )


def test_academic_term_number_uniqueness_is_enforced_at_the_database_level(
    institution_factory,
):
    institution = institution_factory()
    with tenant_context(institution.id):
        year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )

        duplicate = AcademicTerm(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=year,
            number=1,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
        )
        with transaction.atomic(), pytest.raises(IntegrityError):
            # Bypasses AcademicTerm.save()'s full_clean() on purpose.
            AcademicTerm.objects.bulk_create([duplicate])


def test_academic_cycle_order_is_unique_per_institution(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        AcademicCycle.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="1.º Ciclo",
            order=1,
        )

        with transaction.atomic(), pytest.raises(IntegrityError):
            AcademicCycle.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                designation="Outro Ciclo",
                order=1,
            )


def test_non_teaching_day_str_includes_date_and_description(institution_factory):
    institution = institution_factory()
    with tenant_context(institution.id):
        day = NonTeachingDay.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            date=date(2026, 1, 1),
            description="Ano Novo",
            scope=NonTeachingDay.Scope.NATIONAL,
        )

    assert str(day) == "Ano Novo (01/01/2026)"
