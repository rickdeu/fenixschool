"""Tests for the `grading` models (issue #18, RF-INST-06,
docs/05-modelo-de-dados.md §5.16)."""

import uuid
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.core.context import tenant_context
from apps.grading.models import EvaluationType, GradingFormulaOverride, GradingScale

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def test_evaluation_type_str_is_its_name(institution):
    with tenant_context(institution.id):
        evaluation_type = EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight=Decimal("0.3"),
        )

    assert str(evaluation_type) == "MAC"


def test_evaluation_type_name_is_unique_per_institution(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight=Decimal("0.3"),
        )

        with pytest.raises(ValidationError):
            EvaluationType.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                name="MAC",
                default_weight=Decimal("0.5"),
            )


def test_evaluation_type_weight_must_be_between_zero_and_one(institution):
    with tenant_context(institution.id), pytest.raises(ValidationError):
        EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight=Decimal("1.5"),
        )


def test_formula_override_requires_exactly_one_of_course_or_subject(institution, course, subject):
    with tenant_context(institution.id):
        with pytest.raises(ValidationError):
            GradingFormulaOverride.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                weights={"MAC": "1"},
            )

        with pytest.raises(ValidationError):
            GradingFormulaOverride.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                course=course,
                subject=subject,
                weights={"MAC": "1"},
            )


def test_formula_override_course_must_belong_to_the_same_institution(institution, course):
    other_institution = type(institution).objects.create(name="Outra Escola")

    with tenant_context(institution.id), pytest.raises(ValidationError):
        GradingFormulaOverride.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            course=course,
            weights={"MAC": "1"},
        )


def test_only_one_override_allowed_per_course(institution, course):
    with tenant_context(institution.id):
        GradingFormulaOverride.objects.create(
            institution=institution, origin_node_id=_origin(), course=course, weights={"MAC": "1"}
        )

        with pytest.raises(ValidationError):
            GradingFormulaOverride.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                course=course,
                weights={"Exame": "1"},
            )


def test_one_override_per_course_constraint_is_enforced_at_the_database_level(institution, course):
    with tenant_context(institution.id):
        GradingFormulaOverride.objects.create(
            institution=institution, origin_node_id=_origin(), course=course, weights={"MAC": "1"}
        )

        second = GradingFormulaOverride(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            weights={"Exame": "1"},
        )
        with transaction.atomic(), pytest.raises(IntegrityError):
            # Bypasses `GradingFormulaOverride.save()`'s `full_clean()` on purpose.
            GradingFormulaOverride.objects.bulk_create([second])


def test_grading_scale_fixture_loads_the_5_official_levels():
    """Decreto Executivo 106/26, Anexo II -- see
    docs/legislacao/escala-avaliacao-secundario.md. Loaded once, from a
    migration (issue #56), not per-institution: this is national reference
    data, not a `SyncedModel`."""
    levels = list(GradingScale.objects.values_list("qualitative_level", "min_value", "max_value"))

    assert levels == [
        ("Excelente", 17, 20),
        ("Bom", 14, 16),
        ("Suficiente", 10, 13),
        ("Insuficiente", 6, 9),
        ("Mau", 0, 5),
    ]


def test_grading_scale_str():
    excelente = GradingScale.objects.get(qualitative_level="Excelente")

    assert str(excelente) == "Excelente (17-20)"


@pytest.mark.parametrize(
    "value, expected_level",
    [
        (20, "Excelente"),
        (17, "Excelente"),
        (16, "Bom"),
        (13, "Suficiente"),
        (10, "Suficiente"),
        (9, "Insuficiente"),
        (5, "Mau"),
        (0, "Mau"),
    ],
)
def test_for_value_returns_the_matching_qualitative_level(value, expected_level):
    assert GradingScale.for_value(value).qualitative_level == expected_level


def test_for_value_returns_none_outside_the_0_20_range():
    assert GradingScale.for_value(21) is None
    assert GradingScale.for_value(-1) is None
