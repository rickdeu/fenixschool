"""Tests for `attendance.Attendance` (issue #65, RF-FREQ-01)."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Profile
from apps.attendance.models import Attendance
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 3, 2)
TUESDAY = date(2026, 3, 3)


def _origin():
    return uuid.uuid4()


@pytest.fixture
def registrar(institution, user_factory):
    return user_factory(profile=Profile.HOMEROOM_TEACHER, institution=institution)


def test_creates_a_present_record(institution, enrollment, student, schedule, registrar):
    with tenant_context(institution.id):
        attendance = Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=MONDAY,
            status=Attendance.Status.PRESENT,
            registered_by=registrar,
        )

    assert attendance.status == Attendance.Status.PRESENT
    assert str(attendance)


@pytest.mark.parametrize(
    "status",
    [Attendance.Status.PRESENT, Attendance.Status.ABSENT, Attendance.Status.JUSTIFIED_ABSENT],
)
def test_supports_all_three_states(institution, enrollment, student, schedule, registrar, status):
    with tenant_context(institution.id):
        attendance = Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=MONDAY,
            status=status,
            registered_by=registrar,
        )

    assert attendance.status == status


def test_rejects_a_date_on_the_wrong_weekday_for_the_schedule(
    institution, enrollment, student, schedule, registrar
):
    """`schedule` meets on Mondays -- a Tuesday date for it is nonsensical."""
    with tenant_context(institution.id):
        with pytest.raises(ValidationError):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=TUESDAY,
                status=Attendance.Status.PRESENT,
                registered_by=registrar,
            )


def test_rejects_an_enrollment_belonging_to_a_different_student(
    institution, enrollment, schedule, registrar, document_type
):
    from apps.enrollment.models import Guardian, Student

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
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="OTHER-001",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )

        with pytest.raises(ValidationError):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=other_student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY,
                status=Attendance.Status.PRESENT,
                registered_by=registrar,
            )


def test_unique_per_enrollment_schedule_and_date(
    institution, enrollment, student, schedule, registrar
):
    with tenant_context(institution.id):
        Attendance.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            enrollment=enrollment,
            schedule=schedule,
            date=MONDAY,
            status=Attendance.Status.PRESENT,
            registered_by=registrar,
        )

        with pytest.raises(ValidationError):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY,
                status=Attendance.Status.ABSENT,
                registered_by=registrar,
            )
