"""Tests for Student/Guardian/StudentGuardian (issues #39, #40, #41,
docs/05-modelo-de-dados.md §5.11-§5.13)."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.core.context import tenant_context
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian, Student, StudentGuardian

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    # Already preloaded as national reference data by the
    # core.0002_reference_data migration -- not created here.
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


def _make_consenting_guardian(institution, document_type, document_number):
    return Guardian.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        full_name="Encarregado de " + document_number,
        kinship=Guardian.Kinship.MOTHER,
        document_type=document_type,
        document_number="CONSENT-" + document_number,
    )


def _make_student(institution, document_type, document_number="123456789LA000"):
    guardian = _make_consenting_guardian(institution, document_type, document_number)
    return Student.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        first_name="Ana",
        last_name="Silva",
        birth_date=date(2010, 5, 20),
        gender=Student.Gender.FEMALE,
        document_type=document_type,
        document_number=document_number,
        document_issue_date=date(2020, 1, 1),
        document_issue_place="Nacional - Luanda",
        guardian_consent_given_by=guardian,
    )


def test_student_number_is_assigned_automatically_and_sequential(institution, document_type):
    with tenant_context(institution.id):
        first = _make_student(institution, document_type, "AAA")
        second = _make_student(institution, document_type, "BBB")

    assert first.student_number == 1
    assert second.student_number == 2


def test_student_number_is_sequential_per_institution(institution, document_type):
    other_institution = type(institution).objects.create(name="Outra Escola")

    with tenant_context(institution.id):
        student_a = _make_student(institution, document_type, "AAA")
    with tenant_context(other_institution.id):
        student_b = _make_student(other_institution, document_type, "AAA")

    assert student_a.student_number == 1
    assert student_b.student_number == 1


def test_student_document_number_is_unique_per_institution(institution, document_type):
    with tenant_context(institution.id):
        _make_student(institution, document_type, "SAME-DOC")

        with pytest.raises(ValidationError):
            _make_student(institution, document_type, "SAME-DOC")


def test_student_document_number_uniqueness_is_enforced_at_the_database_level(
    institution, document_type
):
    with tenant_context(institution.id):
        _make_student(institution, document_type, "SAME-DOC")
        guardian = _make_consenting_guardian(institution, document_type, "OTHER")

        duplicate = Student(
            institution=institution,
            origin_node_id=_origin(),
            student_number=999,
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2010, 5, 20),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="SAME-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )
        with transaction.atomic(), pytest.raises(IntegrityError):
            Student.objects.bulk_create([duplicate])


def test_student_can_use_any_province_since_it_is_shared_national_reference_data(
    institution, document_type
):
    from apps.core.models import Province

    any_province = Province.objects.get(code="luanda")

    with tenant_context(institution.id):
        guardian = _make_consenting_guardian(institution, document_type, "XYZ")
        student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Ana",
            last_name="Silva",
            birth_date=date(2010, 5, 20),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="XYZ",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            province=any_province,
            guardian_consent_given_by=guardian,
        )

    assert student.province == any_province


def test_guardian_str_is_its_full_name(institution, document_type):
    with tenant_context(institution.id):
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="José Silva",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="987654321LA000",
        )

    assert str(guardian) == "José Silva"


def test_guardian_optionally_links_to_a_user(institution, document_type, user_factory):
    with tenant_context(institution.id):
        portal_user = user_factory(institution=institution)
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="José Silva",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="987654321LA000",
            user=portal_user,
        )

    assert guardian.user == portal_user
    assert portal_user.guardian_profile == guardian


def test_student_can_have_multiple_guardians_with_one_primary(institution, document_type):
    with tenant_context(institution.id):
        student = _make_student(institution, document_type)
        father = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="José Silva",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="FATHER-DOC",
        )
        mother = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Maria Silva",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="MOTHER-DOC",
        )

        StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=father,
            is_primary=False,
        )
        primary_link = StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=mother,
            is_primary=True,
            financially_responsible=True,
        )

        # `student.guardian_links` is a reverse relation manager backed by
        # `StudentGuardian.objects` (the tenant-filtered manager), so it
        # must be read inside the same tenant context that created the rows.
        assert student.guardian_links.count() == 2

    assert primary_link.is_primary


def test_only_one_primary_guardian_per_student(institution, document_type):
    with tenant_context(institution.id):
        student = _make_student(institution, document_type)
        father = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="José Silva",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="FATHER-DOC",
        )
        mother = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Maria Silva",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="MOTHER-DOC",
        )
        StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=father,
            is_primary=True,
        )

        with pytest.raises(ValidationError):
            StudentGuardian.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                guardian=mother,
                is_primary=True,
            )


def test_student_guardian_pair_is_unique(institution, document_type):
    with tenant_context(institution.id):
        student = _make_student(institution, document_type)
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="José Silva",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="FATHER-DOC",
        )
        StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=guardian,
        )

        with pytest.raises(ValidationError):
            StudentGuardian.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                guardian=guardian,
            )


def test_student_guardian_student_and_guardian_must_share_institution(institution, document_type):
    other_institution = type(institution).objects.create(name="Outra Escola")
    with tenant_context(institution.id):
        student = _make_student(institution, document_type)
    with tenant_context(other_institution.id):
        foreign_document_type = IdentificationDocumentType.objects.first()
        foreign_guardian = Guardian.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            full_name="Estranho",
            kinship=Guardian.Kinship.OTHER,
            document_type=foreign_document_type,
            document_number="FOREIGN-DOC",
        )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        StudentGuardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            guardian=foreign_guardian,
        )


def test_student_cannot_be_created_without_guardian_consent(institution, document_type):
    """Issue #143, RNF-AUD-02 (Lei 22/11): enforced structurally at the model
    level -- `guardian_consent_given_by` has no default and is not nullable."""
    with tenant_context(institution.id), pytest.raises(ValidationError):
        Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Ana",
            last_name="Silva",
            birth_date=date(2010, 5, 20),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="NO-CONSENT",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )


def test_student_records_who_consented_and_when(institution, document_type):
    with tenant_context(institution.id):
        guardian = _make_consenting_guardian(institution, document_type, "CONSENT-CHECK")
        student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Ana",
            last_name="Silva",
            birth_date=date(2010, 5, 20),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="CONSENT-CHECK",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )

    assert student.guardian_consent_given_by == guardian
    assert student.guardian_consent_given_at is not None
