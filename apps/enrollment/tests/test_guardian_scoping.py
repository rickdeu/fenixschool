"""Tests for Encarregado de Educação object-level scoping (issue #29,
docs/07-perfis-permissoes-e-fluxos.md §7.2: "só vê os seus educandos").
"""

import uuid
from datetime import date

import pytest

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian, Student, StudentGuardian
from apps.enrollment.services import get_enrollments_for_guardian, get_students_for_guardian

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


def _make_guardian(institution, document_type, *, document_number, user=None):
    return Guardian.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        full_name=f"Encarregado {document_number}",
        kinship=Guardian.Kinship.MOTHER,
        document_type=document_type,
        document_number=document_number,
        user=user,
    )


def _make_student(institution, document_type, guardian, *, document_number):
    return Student.objects.create(
        institution=institution,
        origin_node_id=_origin(),
        first_name="Aluno",
        last_name=document_number,
        birth_date=date(2010, 1, 1),
        gender=Student.Gender.FEMALE,
        document_type=document_type,
        document_number=document_number,
        document_issue_date=date(2020, 1, 1),
        document_issue_place="Luanda",
        guardian_consent_given_by=guardian,
    )


def _link(institution, student, guardian):
    return StudentGuardian.objects.create(
        institution=institution, origin_node_id=_origin(), student=student, guardian=guardian
    )


@pytest.fixture
def two_guardians_with_one_student_each(institution, document_type):
    with tenant_context(institution.id):
        user_a = User.objects.create_user(username="enc_a", profile=Profile.GUARDIAN, password="x")
        user_b = User.objects.create_user(username="enc_b", profile=Profile.GUARDIAN, password="x")
        guardian_a = _make_guardian(
            institution, document_type, document_number="ENC-A", user=user_a
        )
        guardian_b = _make_guardian(
            institution, document_type, document_number="ENC-B", user=user_b
        )
        student_a = _make_student(institution, document_type, guardian_a, document_number="ALU-A")
        student_b = _make_student(institution, document_type, guardian_b, document_number="ALU-B")
        _link(institution, student_a, guardian_a)
        _link(institution, student_b, guardian_b)
    return {
        "user_a": user_a,
        "user_b": user_b,
        "student_a": student_a,
        "student_b": student_b,
    }


def test_guardian_sees_only_their_own_student(two_guardians_with_one_student_each, institution):
    data = two_guardians_with_one_student_each

    with tenant_context(institution.id):
        visible_to_a = list(get_students_for_guardian(data["user_a"]))

    assert visible_to_a == [data["student_a"]]


def test_guardian_cannot_see_another_guardians_student(
    two_guardians_with_one_student_each, institution
):
    data = two_guardians_with_one_student_each

    with tenant_context(institution.id):
        visible_to_a = get_students_for_guardian(data["user_a"])

    assert data["student_b"] not in visible_to_a


def test_a_student_with_two_guardians_is_visible_to_both(institution, document_type):
    with tenant_context(institution.id):
        user_mother = User.objects.create_user(
            username="mae", profile=Profile.GUARDIAN, password="x"
        )
        user_father = User.objects.create_user(
            username="pai", profile=Profile.GUARDIAN, password="x"
        )
        mother = _make_guardian(institution, document_type, document_number="MAE", user=user_mother)
        father = _make_guardian(institution, document_type, document_number="PAI", user=user_father)
        student = _make_student(institution, document_type, mother, document_number="FILHO")
        _link(institution, student, mother)
        _link(institution, student, father)

        assert list(get_students_for_guardian(user_mother)) == [student]
        assert list(get_students_for_guardian(user_father)) == [student]


def test_a_revoked_guardian_link_no_longer_grants_access(institution, document_type):
    with tenant_context(institution.id):
        user = User.objects.create_user(username="enc1", profile=Profile.GUARDIAN, password="x")
        guardian = _make_guardian(institution, document_type, document_number="ENC-1", user=user)
        student = _make_student(institution, document_type, guardian, document_number="ALU-1")
        link = _link(institution, student, guardian)

        assert list(get_students_for_guardian(user)) == [student]

        link.is_deleted = True
        link.save(update_fields=["is_deleted"])

        assert list(get_students_for_guardian(user)) == []


def test_a_user_with_no_guardian_record_sees_no_students(institution):
    with tenant_context(institution.id):
        non_guardian = User.objects.create_user(
            username="prof1", profile=Profile.TEACHER, password="x"
        )

        assert list(get_students_for_guardian(non_guardian)) == []


def test_enrollments_are_scoped_the_same_way(institution, document_type):
    """`enrollment.Enrollment.objects.for_guardian` -- same relationship,
    same isolation, for the Matrícula side of the same §7.2 row."""
    from apps.academic.models import Course, CurricularYear, Department, SchoolClass
    from apps.core.models import AcademicCycle, AcademicYear
    from apps.enrollment.models import Enrollment

    with tenant_context(institution.id):
        user_a = User.objects.create_user(username="enc_x", profile=Profile.GUARDIAN, password="x")
        user_b = User.objects.create_user(username="enc_y", profile=Profile.GUARDIAN, password="x")
        guardian_a = _make_guardian(
            institution, document_type, document_number="ENC-X", user=user_a
        )
        guardian_b = _make_guardian(
            institution, document_type, document_number="ENC-Y", user=user_b
        )
        student_a = _make_student(institution, document_type, guardian_a, document_number="ALU-X")
        student_b = _make_student(institution, document_type, guardian_b, document_number="ALU-Y")
        _link(institution, student_a, guardian_a)
        _link(institution, student_b, guardian_b)

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
        )
        enrollment_a = Enrollment.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student_a,
            school_class=school_class,
            course=course,
            academic_year=academic_year,
            cycle=cycle,
            curricular_year=curricular_year,
            presented_document_type=document_type,
            presented_document_number="ALU-X-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )
        Enrollment.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student_b,
            school_class=school_class,
            course=course,
            academic_year=academic_year,
            cycle=cycle,
            curricular_year=curricular_year,
            presented_document_type=document_type,
            presented_document_number="ALU-Y-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )

        visible_to_a = list(get_enrollments_for_guardian(user_a))

    assert visible_to_a == [enrollment_a]
