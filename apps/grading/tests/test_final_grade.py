"""Tests for the FinalGrade model (issue #58, RF-AVAL-02)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import CurricularYear, Subject
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import FinalGrade

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def _make_final_grade(institution, enrollment, subject, academic_term, **overrides):
    data = {
        "institution": institution,
        "origin_node_id": _origin(),
        "enrollment": enrollment,
        "subject": subject,
        "academic_term": academic_term,
        "calculated_value": Decimal("15"),
    }
    data.update(overrides)
    return FinalGrade.objects.create(**data)


def test_final_value_returns_the_calculated_value_when_no_override(
    institution, enrollment, subject, academic_term
):
    with tenant_context(institution.id):
        final_grade = _make_final_grade(institution, enrollment, subject, academic_term)

    assert final_grade.final_value == Decimal("15")


def test_final_value_returns_the_manual_override_when_present(
    institution, enrollment, subject, academic_term
):
    with tenant_context(institution.id):
        final_grade = _make_final_grade(
            institution,
            enrollment,
            subject,
            academic_term,
            manual_override_value=Decimal("18"),
            override_reason="Trabalho extra avaliado.",
        )

    assert final_grade.final_value == Decimal("18")


def test_qualitative_level_matches_the_final_value_not_the_calculated_one(
    institution, enrollment, subject, academic_term
):
    with tenant_context(institution.id):
        final_grade = _make_final_grade(
            institution,
            enrollment,
            subject,
            academic_term,
            calculated_value=Decimal("8"),
            manual_override_value=Decimal("18"),
            override_reason="Recurso.",
        )

    assert final_grade.qualitative_level.qualitative_level == "Excelente"


def test_manual_override_value_requires_a_reason(institution, enrollment, subject, academic_term):
    with tenant_context(institution.id), pytest.raises(ValidationError):
        _make_final_grade(
            institution, enrollment, subject, academic_term, manual_override_value=Decimal("18")
        )


def test_subject_must_belong_to_the_enrollments_curricular_year(
    institution, enrollment, subject, academic_term, course
):
    with tenant_context(institution.id):
        other_curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=2,
            equivalent_grade="11.ª classe",
        )
        other_subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="FIS",
            name="Física",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=other_curricular_year,
            cycle=enrollment.cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )

        with pytest.raises(ValidationError):
            _make_final_grade(institution, enrollment, other_subject, academic_term)


def test_overridden_by_must_belong_to_the_same_institution(
    institution, enrollment, subject, academic_term
):
    from apps.core.factories import InstitutionFactory

    other_institution = InstitutionFactory()
    with tenant_context(institution.id):
        other_teacher = User.objects.create_user(
            username="professor-outro", institution=other_institution, profile=Profile.TEACHER
        )

        with pytest.raises(ValidationError):
            _make_final_grade(
                institution,
                enrollment,
                subject,
                academic_term,
                manual_override_value=Decimal("18"),
                override_reason="Ajuste.",
                overridden_by=other_teacher,
            )


def test_unique_constraint_per_enrollment_subject_term(
    institution, enrollment, subject, academic_term
):
    with tenant_context(institution.id):
        _make_final_grade(institution, enrollment, subject, academic_term)

        with pytest.raises(ValidationError):
            _make_final_grade(institution, enrollment, subject, academic_term)


def test_str(institution, enrollment, subject, academic_term):
    with tenant_context(institution.id):
        final_grade = _make_final_grade(institution, enrollment, subject, academic_term)

    assert "Yolene Hangalo" in str(final_grade)
    assert "Matemática" in str(final_grade)
