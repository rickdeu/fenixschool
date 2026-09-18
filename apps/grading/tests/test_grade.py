"""Tests for the Nota model (RF-AVAL-01, docs/05-modelo-de-dados.md §5.17,
issue #55)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import Course, CurricularYear, Department, SchoolClass, Subject
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicTerm, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Guardian, Student
from apps.enrollment.services import enroll_student
from apps.grading.models import EvaluationType, Grade, GradeReportClosedError

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def setup(institution, document_type):
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
        subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT",
            name="Matemática",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )
        academic_year = AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )
        academic_term = AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=academic_year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
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
        )
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-1",
        )
        student = Student.objects.create(
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
        enrollment = enroll_student(
            institution=institution,
            student=student,
            school_class=school_class,
            origin_node_id=_origin(),
            course=course,
            academic_year=academic_year,
            cycle=cycle,
            curricular_year=curricular_year,
            presented_document_type=document_type,
            presented_document_number=student.document_number,
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )
        evaluation_type = EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight=Decimal("0.3"),
        )
    teacher = User.objects.create_user(
        username="professor1", institution=institution, profile=Profile.TEACHER, password="x"
    )
    return {
        "institution": institution,
        "department": department,
        "course": course,
        "curricular_year": curricular_year,
        "subject": subject,
        "academic_year": academic_year,
        "academic_term": academic_term,
        "cycle": cycle,
        "school_class": school_class,
        "student": student,
        "enrollment": enrollment,
        "evaluation_type": evaluation_type,
        "teacher": teacher,
    }


def _make_grade(setup, **overrides):
    data = {
        "institution": setup["institution"],
        "origin_node_id": _origin(),
        "student": setup["student"],
        "enrollment": setup["enrollment"],
        "subject": setup["subject"],
        "academic_term": setup["academic_term"],
        "evaluation_type": setup["evaluation_type"],
        "value": Decimal("15.5"),
        "teacher": setup["teacher"],
    }
    data.update(overrides)
    return Grade.objects.create(**data)


def test_creating_a_grade_derives_the_denormalized_fields(setup):
    with tenant_context(setup["institution"].id):
        grade = _make_grade(setup)

    assert grade.course_id == setup["course"].id
    assert grade.academic_year_id == setup["academic_year"].id
    assert grade.cycle_id == setup["cycle"].id
    assert grade.curricular_year_id == setup["curricular_year"].id
    assert grade.school_class_id == setup["school_class"].id
    assert grade.department_id == setup["department"].id


def test_qualitative_level_matches_the_official_grading_scale(setup):
    with tenant_context(setup["institution"].id):
        grade = _make_grade(setup, value=Decimal("15"))

    assert grade.qualitative_level.qualitative_level == "Bom"


def test_str(setup):
    with tenant_context(setup["institution"].id):
        grade = _make_grade(setup)

    assert "Yolene Hangalo" in str(grade)
    assert "Matemática" in str(grade)
    assert "MAC" in str(grade)
    assert "15.5" in str(grade)


def test_value_must_be_within_0_and_20(setup):
    with tenant_context(setup["institution"].id), pytest.raises(ValidationError):
        _make_grade(setup, value=Decimal("20.1"))

    with tenant_context(setup["institution"].id), pytest.raises(ValidationError):
        _make_grade(setup, value=Decimal("-0.1"))


def test_teacher_must_have_a_teaching_profile(setup, institution):
    non_teacher = User.objects.create_user(
        username="secretaria1", institution=institution, profile=Profile.SECRETARY, password="x"
    )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        _make_grade(setup, teacher=non_teacher)


def test_enrollment_must_belong_to_the_same_student(setup, institution, document_type):
    with tenant_context(institution.id):
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Outro Encarregado",
            kinship=Guardian.Kinship.FATHER,
            document_type=document_type,
            document_number="ENC-2",
        )
        other_student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Ana",
            last_name="Kavungo",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="OTHER-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )

        with pytest.raises(ValidationError):
            _make_grade(setup, student=other_student)


def test_subject_must_belong_to_the_enrollments_curricular_year(setup, institution):
    with tenant_context(institution.id):
        other_curricular_year = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=setup["course"],
            number=2,
            equivalent_grade="11.ª classe",
        )
        other_subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="FIS",
            name="Física",
            created_on=date(2020, 1, 1),
            course=setup["course"],
            curricular_year=other_curricular_year,
            cycle=setup["cycle"],
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )

        with pytest.raises(ValidationError):
            _make_grade(setup, subject=other_subject)


def test_only_one_grade_per_student_subject_term_and_evaluation_type(setup):
    with tenant_context(setup["institution"].id):
        _make_grade(setup)

        with pytest.raises(ValidationError):
            _make_grade(setup)


def test_editing_a_grade_is_blocked_once_its_pauta_is_closed(setup):
    with tenant_context(setup["institution"].id):
        grade = _make_grade(setup)
        grade.is_grade_report_closed = True
        grade.save(authorize_closed_edit=True)

        grade.value = Decimal("18")
        with pytest.raises(GradeReportClosedError):
            grade.save()


def test_editing_a_closed_grade_with_explicit_authorization_succeeds(setup):
    with tenant_context(setup["institution"].id):
        grade = _make_grade(setup)
        grade.is_grade_report_closed = True
        grade.save(authorize_closed_edit=True)

        grade.value = Decimal("18")
        grade.save(authorize_closed_edit=True)
        grade.refresh_from_db()

    assert grade.value == Decimal("18.0")


def test_creating_a_new_grade_is_never_blocked_by_the_closed_pauta_check(setup):
    """The block only ever applies to *editing* an existing row -- a brand
    new Grade has no `pk` yet, so there is no "current" closed state to
    conflict with."""
    with tenant_context(setup["institution"].id):
        _make_grade(setup)  # must not raise
