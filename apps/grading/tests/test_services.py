"""Tests for the `grading` services (issue #18, RF-INST-06)."""

import uuid
from decimal import Decimal

import pytest

from apps.core.context import tenant_context
from apps.grading.models import EvaluationType, GradingFormulaOverride
from apps.grading.services import (
    InvalidGradingFormulaError,
    calculate_average,
    ensure_default_evaluation_types,
    resolve_grading_formula,
    seed_default_grading_formula,
    set_course_formula_override,
    set_institution_default_formula,
    set_subject_formula_override,
    validate_formula,
)

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def test_ensure_default_evaluation_types_seeds_mac_pt_exame(institution):
    with tenant_context(institution.id):
        types = ensure_default_evaluation_types(institution, origin_node_id=_origin())

    assert {t.name for t in types} == {"MAC", "Prova Trimestral", "Exame"}
    assert sum(t.default_weight for t in types) == Decimal("1.0")


def test_ensure_default_evaluation_types_is_idempotent(institution):
    with tenant_context(institution.id):
        ensure_default_evaluation_types(institution, origin_node_id=_origin())
        types = ensure_default_evaluation_types(institution, origin_node_id=_origin())

    assert len(types) == 3


def test_ensure_default_evaluation_types_does_not_duplicate_a_custom_type(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.5"
        )
        types = ensure_default_evaluation_types(institution, origin_node_id=_origin())

    macs = [t for t in types if t.name == "MAC"]
    assert len(macs) == 1
    assert macs[0].default_weight == Decimal("0.5")


def test_validate_formula_rejects_empty_formula(institution):
    with tenant_context(institution.id), pytest.raises(InvalidGradingFormulaError):
        validate_formula({}, institution=institution)


def test_validate_formula_rejects_unknown_evaluation_type(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="1"
        )
        with pytest.raises(InvalidGradingFormulaError, match="desconhecido"):
            validate_formula({"Não Existe": Decimal("1")}, institution=institution)


def test_validate_formula_rejects_weights_not_summing_to_one(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.3"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.4"
        )
        with pytest.raises(InvalidGradingFormulaError, match="soma"):
            validate_formula(
                {"MAC": Decimal("0.3"), "Exame": Decimal("0.4")}, institution=institution
            )


def test_validate_formula_accepts_weights_summing_to_one(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.3"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.4"
        )
        # Does not raise.
        validate_formula(
            {"MAC": Decimal("0.6"), "Exame": Decimal("0.4")}, institution=institution
        )


def test_set_institution_default_formula_persists_it(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.6"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.4"
        )
        set_institution_default_formula(
            institution, {"MAC": Decimal("0.6"), "Exame": Decimal("0.4")}
        )
        institution.refresh_from_db()

    assert institution.default_grading_formula == {"MAC": "0.6", "Exame": "0.4"}


def test_set_institution_default_formula_rejects_an_invalid_formula(institution):
    with tenant_context(institution.id):
        with pytest.raises(InvalidGradingFormulaError):
            set_institution_default_formula(institution, {"MAC": Decimal("0.5")})


def test_course_override_takes_precedence_over_institution_default(institution, course):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.5"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.5"
        )
        set_institution_default_formula(
            institution, {"MAC": Decimal("0.5"), "Exame": Decimal("0.5")}
        )
        set_course_formula_override(
            course, {"MAC": Decimal("0.2"), "Exame": Decimal("0.8")}, origin_node_id=_origin()
        )

        resolved = resolve_grading_formula(institution=institution, course=course)

    assert resolved == {"MAC": Decimal("0.2"), "Exame": Decimal("0.8")}


def test_subject_override_takes_precedence_over_course_override(institution, course, subject):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.5"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.5"
        )
        set_course_formula_override(
            course, {"MAC": Decimal("0.2"), "Exame": Decimal("0.8")}, origin_node_id=_origin()
        )
        set_subject_formula_override(
            subject, {"MAC": Decimal("0.9"), "Exame": Decimal("0.1")}, origin_node_id=_origin()
        )

        resolved = resolve_grading_formula(institution=institution, course=course, subject=subject)

    assert resolved == {"MAC": Decimal("0.9"), "Exame": Decimal("0.1")}


def test_resolve_falls_back_to_institution_default_without_any_override(institution, course):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="0.5"
        )
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="Exame", default_weight="0.5"
        )
        set_institution_default_formula(
            institution, {"MAC": Decimal("0.5"), "Exame": Decimal("0.5")}
        )

        resolved = resolve_grading_formula(institution=institution, course=course)

    assert resolved == {"MAC": Decimal("0.5"), "Exame": Decimal("0.5")}


def test_clearing_a_course_override_falls_back_to_the_institution_default(institution, course):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="1"
        )
        set_institution_default_formula(institution, {"MAC": Decimal("1")})
        set_course_formula_override(course, {"MAC": Decimal("1")}, origin_node_id=_origin())
        assert GradingFormulaOverride.objects.filter(course=course).exists()

        set_course_formula_override(course, None, origin_node_id=_origin())

        assert not GradingFormulaOverride.objects.filter(course=course).exists()
        resolved = resolve_grading_formula(institution=institution, course=course)

    assert resolved == {"MAC": Decimal("1")}


def test_calculate_average_applies_the_weights(institution):
    average = calculate_average(
        grades={"MAC": Decimal("14"), "PT": Decimal("16"), "Exame": Decimal("12")},
        formula={"MAC": Decimal("0.3"), "PT": Decimal("0.3"), "Exame": Decimal("0.4")},
    )

    assert average == Decimal("14") * Decimal("0.3") + Decimal("16") * Decimal(
        "0.3"
    ) + Decimal("12") * Decimal("0.4")


def test_seed_default_grading_formula_activates_a_working_formula(institution):
    with tenant_context(institution.id):
        seed_default_grading_formula(institution, origin_node_id=_origin())
        institution.refresh_from_db()

    assert institution.default_grading_formula == {
        "MAC": "0.300",
        "Prova Trimestral": "0.300",
        "Exame": "0.400",
    }


def test_seed_default_grading_formula_never_overwrites_a_customised_formula(institution):
    with tenant_context(institution.id):
        EvaluationType.objects.create(
            institution=institution, origin_node_id=_origin(), name="MAC", default_weight="1"
        )
        set_institution_default_formula(institution, {"MAC": Decimal("1")})

        seed_default_grading_formula(institution, origin_node_id=_origin())
        institution.refresh_from_db()

    assert institution.default_grading_formula == {"MAC": "1"}


def test_calculate_average_raises_when_a_grade_is_missing():
    with pytest.raises(ValueError, match="Exame"):
        calculate_average(
            grades={"MAC": Decimal("14")},
            formula={"MAC": Decimal("0.6"), "Exame": Decimal("0.4")},
        )
