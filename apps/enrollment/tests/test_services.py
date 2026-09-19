"""Tests for `apps/enrollment/services.py` (issues #44, #46)."""

import uuid
from datetime import date

import pytest

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Enrollment, Guardian, Student
from apps.enrollment.services import (
    DuplicateStudentDocumentError,
    MissingGuardianConsentError,
    SchoolClassFullError,
    StudentAlreadyEnrolledError,
    enroll_student,
    register_student,
)

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


def _make_guardian(institution, document_type, document_number="CONSENT-000"):
    return Guardian.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        full_name="Encarregado",
        kinship=Guardian.Kinship.MOTHER,
        document_type=document_type,
        document_number=document_number,
    )


def test_register_student_replicates_the_original_document_example(institution, document_type):
    """Issue #44's acceptance criterion: "Teste replicando o exemplo do
    documento original (aluna Yolene Hangalo)" -- docs/06-modulos-e-
    funcionalidades.md §6.4."""
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type)
        student = register_student(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Yolene",
            last_name="Hangalo",
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="005LA00123",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )

    assert student.student_number == 1
    assert str(student) == "Yolene Hangalo (#1)"


def test_register_student_blocks_missing_guardian_consent(institution, document_type):
    """Issue #143's acceptance criterion: "Inscrição bloqueada sem
    consentimento registado"."""
    with tenant_context(institution.id):
        with pytest.raises(MissingGuardianConsentError):
            register_student(
                institution=institution,
                origin_node_id=_origin(),
                first_name="Yolene",
                last_name="Hangalo",
                birth_date=date(2012, 4, 10),
                gender=Student.Gender.FEMALE,
                document_type=document_type,
                document_number="005LA00123",
                document_issue_date=date(2020, 1, 1),
                document_issue_place="Nacional - Luanda",
                guardian_consent_given_by=None,
            )

        assert not Student.objects.filter(document_number="005LA00123").exists()


def test_register_student_blocks_duplicate_document(institution, document_type):
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type)
        register_student(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Yolene",
            last_name="Hangalo",
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="005LA00123",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )

        with pytest.raises(DuplicateStudentDocumentError):
            register_student(
                institution=institution,
                origin_node_id=_origin(),
                first_name="Outro",
                last_name="Aluno",
                birth_date=date(2011, 1, 1),
                gender=Student.Gender.MALE,
                document_type=document_type,
                document_number="005LA00123",
                document_issue_date=date(2020, 1, 1),
                document_issue_place="Nacional - Luanda",
                guardian_consent_given_by=guardian,
            )

        assert Student.objects.filter(document_number="005LA00123").count() == 1


def test_register_student_blocks_duplicate_even_against_a_soft_deleted_record(
    institution, document_type
):
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type)
        existing = register_student(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Yolene",
            last_name="Hangalo",
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="005LA00123",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )
        existing.is_deleted = True
        existing.save()

        with pytest.raises(DuplicateStudentDocumentError):
            register_student(
                institution=institution,
                origin_node_id=_origin(),
                first_name="Outro",
                last_name="Aluno",
                birth_date=date(2011, 1, 1),
                gender=Student.Gender.MALE,
                document_type=document_type,
                document_number="005LA00123",
                document_issue_date=date(2020, 1, 1),
                document_issue_place="Nacional - Luanda",
                guardian_consent_given_by=guardian,
            )


@pytest.fixture
def class_setup(institution, document_type):
    with tenant_context(institution.id):
        department = Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )
        cycle = AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )
        course = Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )
        curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        school_class = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
            max_enrollment=2,
        )
    return {
        "course": course,
        "cycle": cycle,
        "curricular_year": curricular_year,
        "academic_year": academic_year,
        "school_class": school_class,
    }


def _make_student(institution, document_type, document_number):
    guardian = _make_guardian(institution, document_type, "CONSENT-" + document_number)
    return Student.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        first_name="Aluno",
        last_name=document_number,
        birth_date=date(2011, 1, 1),
        gender=Student.Gender.MALE,
        document_type=document_type,
        document_number=document_number,
        document_issue_date=date(2020, 1, 1),
        document_issue_place="Nacional - Luanda",
        guardian_consent_given_by=guardian,
    )


def _enroll(institution, class_setup, student, **overrides):
    return enroll_student(
        institution=institution,
        student=student,
        school_class=class_setup["school_class"],
        origin_node_id=_origin(),
        course=class_setup["course"],
        academic_year=class_setup["academic_year"],
        cycle=class_setup["cycle"],
        curricular_year=class_setup["curricular_year"],
        presented_document_type=student.document_type,
        presented_document_number=student.document_number,
        document_issue_date=date(2020, 1, 1),
        document_issue_place="Nacional - Luanda",
        **overrides,
    )


def test_enroll_student_succeeds_up_to_the_last_available_vacancy(
    institution, document_type, class_setup
):
    """Issue #46's acceptance criterion: boundary test (the last available vacancy)."""
    with tenant_context(institution.id):
        first = _make_student(institution, document_type, "AAA")
        second = _make_student(institution, document_type, "BBB")

        _enroll(institution, class_setup, first)
        # max_enrollment=2: this is the last available vacancy, must succeed.
        enrollment = _enroll(institution, class_setup, second)

        assert isinstance(enrollment, Enrollment)
        assert class_setup["school_class"].active_enrollment_count() == 2


def test_enroll_student_blocks_once_the_class_is_full(institution, document_type, class_setup):
    with tenant_context(institution.id):
        first = _make_student(institution, document_type, "AAA")
        second = _make_student(institution, document_type, "BBB")
        third = _make_student(institution, document_type, "CCC")

        _enroll(institution, class_setup, first)
        _enroll(institution, class_setup, second)

        with pytest.raises(SchoolClassFullError):
            _enroll(institution, class_setup, third)


def test_cancelled_enrollments_free_up_a_vacancy(institution, document_type, class_setup):
    with tenant_context(institution.id):
        first = _make_student(institution, document_type, "AAA")
        second = _make_student(institution, document_type, "BBB")
        third = _make_student(institution, document_type, "CCC")

        first_enrollment = _enroll(institution, class_setup, first)
        _enroll(institution, class_setup, second)

        first_enrollment.status = Enrollment.Status.CANCELLED
        first_enrollment.cancellation_reason = "Desistência do aluno."
        first_enrollment.save()

        # A vacancy freed up by the cancellation must be usable again.
        _enroll(institution, class_setup, third)


def test_force_enrolls_past_capacity_instead_of_blocking(institution, document_type, class_setup):
    """Issue #174's "aviso, não bloqueio automático" extends to the
    enrolment action itself -- `force=True` is the Secretaria's explicit
    confirmation past the warning, not a way around real data integrity
    rules (see the next test)."""
    with tenant_context(institution.id):
        first = _make_student(institution, document_type, "AAA")
        second = _make_student(institution, document_type, "BBB")
        third = _make_student(institution, document_type, "CCC")

        _enroll(institution, class_setup, first)
        _enroll(institution, class_setup, second)

        with pytest.raises(SchoolClassFullError):
            _enroll(institution, class_setup, third)

        enrollment = _enroll(institution, class_setup, third, force=True)

        assert isinstance(enrollment, Enrollment)
        assert class_setup["school_class"].active_enrollment_count() == 3


def test_a_student_cannot_have_two_active_enrollments_in_the_same_academic_year(
    institution, document_type, class_setup
):
    with tenant_context(institution.id):
        student = _make_student(institution, document_type, "AAA")
        _enroll(institution, class_setup, student)

        with pytest.raises(StudentAlreadyEnrolledError):
            _enroll(institution, class_setup, student)

        # `force=True` overrides the capacity warning, never this rule --
        # a duplicate matrícula in the same year is always a data error.
        with pytest.raises(StudentAlreadyEnrolledError):
            _enroll(institution, class_setup, student, force=True)

        assert Enrollment.all_objects.filter(student=student).count() == 1
