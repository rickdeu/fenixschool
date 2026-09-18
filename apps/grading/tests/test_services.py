"""Tests for the `grading` services (issue #18, RF-INST-06; issue #57, RF-AVAL-01/03)."""

import uuid
from decimal import Decimal

import pytest

from apps.academic.models import Schedule, SchoolClass
from apps.core.context import tenant_context
from apps.grading.models import EvaluationType, Grade, GradingFormulaOverride
from apps.grading.services import (
    DocenteNaoAssociadoError,
    InvalidGradingFormulaError,
    NotaForaDaEscalaError,
    calculate_average,
    ensure_default_evaluation_types,
    lancar_nota,
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


def test_lancar_nota_creates_a_grade_for_the_scheduled_teacher(
    institution, enrollment, subject, evaluation_type, academic_term, teacher, schedule
):
    with tenant_context(institution.id):
        grade = lancar_nota(
            teacher=teacher,
            enrollment=enrollment,
            subject=subject,
            evaluation_type=evaluation_type,
            academic_term=academic_term,
            value=Decimal("15.5"),
            origin_node_id=uuid.uuid4(),
        )

        assert Grade.objects.filter(pk=grade.pk).exists()

    assert grade.pk is not None
    assert grade.student_id == enrollment.student_id
    assert grade.value == Decimal("15.5")


def test_lancar_nota_rejects_a_value_outside_the_0_20_scale(
    institution, enrollment, subject, evaluation_type, academic_term, teacher, schedule
):
    with tenant_context(institution.id):
        with pytest.raises(NotaForaDaEscalaError):
            lancar_nota(
                teacher=teacher,
                enrollment=enrollment,
                subject=subject,
                evaluation_type=evaluation_type,
                academic_term=academic_term,
                value=Decimal("20.5"),
                origin_node_id=uuid.uuid4(),
            )

    assert not Grade.all_objects.exists()


def test_lancar_nota_rejects_a_teacher_not_scheduled_for_that_turma_disciplina(
    institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    """No `schedule` fixture here on purpose: `teacher` has no
    `academic.Schedule` row associating them with `enrollment.school_class`/
    `subject` at all, so `lancar_nota` must refuse to launch the Nota."""
    with tenant_context(institution.id):
        with pytest.raises(DocenteNaoAssociadoError):
            lancar_nota(
                teacher=teacher,
                enrollment=enrollment,
                subject=subject,
                evaluation_type=evaluation_type,
                academic_term=academic_term,
                value=Decimal("15"),
                origin_node_id=uuid.uuid4(),
            )

    assert not Grade.all_objects.exists()


def test_lancar_nota_rejects_a_teacher_scheduled_for_a_different_turma(
    institution,
    enrollment,
    subject,
    evaluation_type,
    academic_term,
    teacher,
    room,
    course,
    academic_year,
    curricular_year,
):
    """The teacher IS scheduled, but for a different turma than the one this
    matrícula belongs to -- still not associated for this specific Nota."""
    from datetime import time

    with tenant_context(institution.id):
        other_school_class = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            code="10B",
            designation="10.ª B",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.AFTERNOON,
        )
        Schedule.objects.create(
            institution=institution,
            origin_node_id=uuid.uuid4(),
            school_class=other_school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 0),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=teacher,
        )

        with pytest.raises(DocenteNaoAssociadoError):
            lancar_nota(
                teacher=teacher,
                enrollment=enrollment,
                subject=subject,
                evaluation_type=evaluation_type,
                academic_term=academic_term,
                value=Decimal("15"),
                origin_node_id=uuid.uuid4(),
            )
