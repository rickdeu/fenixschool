"""Tests for `apps.academic.services.validate_schedule_conflict` (RF-CURR-06,
issue #37)."""

import uuid
from datetime import date, time

import pytest

from apps.academic.models import (
    Course,
    CurricularYear,
    Department,
    Room,
    Schedule,
    SchoolClass,
    Subject,
)
from apps.academic.services import ScheduleConflictError, validate_schedule_conflict
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


@pytest.fixture
def cycle(institution):
    with tenant_context(institution.id):
        return AcademicCycle.objects.create(
            institution=institution, origin_node_id=_origin(), designation="1.º Ciclo", order=1
        )


@pytest.fixture
def department(institution):
    with tenant_context(institution.id):
        return Department.objects.create(
            institution=institution, origin_node_id=_origin(), name="Ciências"
        )


@pytest.fixture
def course(institution, department, cycle):
    with tenant_context(institution.id):
        return Course.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="INF",
            name="Informática",
            created_on=date(2020, 1, 1),
            department=department,
            cycle=cycle,
            duration_years=4,
        )


@pytest.fixture
def curricular_year(institution, course):
    with tenant_context(institution.id):
        return CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )


@pytest.fixture
def subject(institution, course, curricular_year, cycle):
    with tenant_context(institution.id):
        return Subject.objects.create(
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


@pytest.fixture
def other_subject(institution, course, curricular_year, cycle):
    with tenant_context(institution.id):
        return Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="POR",
            name="Português",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=curricular_year,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )


@pytest.fixture
def academic_year(institution):
    with tenant_context(institution.id):
        return AcademicYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            designation="2026/2027",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 12, 15),
        )


@pytest.fixture
def school_class(institution, course, curricular_year, academic_year):
    with tenant_context(institution.id):
        return SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )


@pytest.fixture
def other_school_class(institution, course, curricular_year, academic_year):
    with tenant_context(institution.id):
        return SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10B",
            designation="10.ª B",
            academic_year=academic_year,
            course=course,
            curricular_year=curricular_year,
            shift=SchoolClass.Shift.MORNING,
        )


@pytest.fixture
def room(institution):
    with tenant_context(institution.id):
        return Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=30
        )


@pytest.fixture
def other_room(institution):
    with tenant_context(institution.id):
        return Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 2", capacity=30
        )


@pytest.fixture
def teacher(institution):
    return User.objects.create_user(
        username="professor1", institution=institution, profile=Profile.TEACHER, password="x"
    )


@pytest.fixture
def other_teacher(institution):
    return User.objects.create_user(
        username="professor2", institution=institution, profile=Profile.TEACHER, password="x"
    )


@pytest.fixture
def existing_schedule(institution, school_class, subject, room, teacher):
    with tenant_context(institution.id):
        return Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=teacher,
        )


def test_no_conflict_for_a_completely_different_slot(
    institution, existing_schedule, other_school_class, other_subject, other_room, other_teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(8, 0),
        end_time=time(9, 30),
        room=other_room,
        teacher=other_teacher,
    )

    validate_schedule_conflict(candidate)  # must not raise


def test_detects_teacher_conflict(
    institution, existing_schedule, other_school_class, other_subject, other_room, teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 0),
        room=other_room,
        teacher=teacher,  # same teacher as existing_schedule
    )

    with pytest.raises(ScheduleConflictError) as excinfo:
        validate_schedule_conflict(candidate)

    assert "docente" in str(excinfo.value)


def test_detects_room_conflict(
    institution, existing_schedule, other_school_class, other_subject, room, other_teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 0),
        room=room,  # same room as existing_schedule
        teacher=other_teacher,
    )

    with pytest.raises(ScheduleConflictError) as excinfo:
        validate_schedule_conflict(candidate)

    assert "sala" in str(excinfo.value)


def test_detects_school_class_conflict(
    institution, existing_schedule, school_class, other_subject, other_room, other_teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=school_class,  # same turma as existing_schedule
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 0),
        room=other_room,
        teacher=other_teacher,
    )

    with pytest.raises(ScheduleConflictError) as excinfo:
        validate_schedule_conflict(candidate)

    assert "turma" in str(excinfo.value)


def test_no_conflict_on_a_different_weekday(
    institution, existing_schedule, other_school_class, other_subject, other_room, teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.TUESDAY,
        start_time=time(8, 0),
        end_time=time(9, 30),
        room=other_room,
        teacher=teacher,
    )

    validate_schedule_conflict(candidate)  # must not raise


def test_back_to_back_slots_do_not_conflict(
    institution, existing_schedule, other_school_class, other_subject, other_room, teacher
):
    """existing_schedule runs 08:00-09:30 -- a slot starting exactly at 09:30
    (same teacher) must not be treated as an overlap."""
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(9, 30),
        end_time=time(11, 0),
        room=other_room,
        teacher=teacher,
    )

    validate_schedule_conflict(candidate)  # must not raise


def test_error_message_identifies_the_conflicting_schedule(
    institution, existing_schedule, other_school_class, other_subject, other_room, teacher
):
    candidate = Schedule(
        institution=institution,
        school_class=other_school_class,
        subject=other_subject,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 0),
        room=other_room,
        teacher=teacher,
    )

    with pytest.raises(ScheduleConflictError) as excinfo:
        validate_schedule_conflict(candidate)

    assert excinfo.value.conflicting_schedule == existing_schedule
    assert "08:00" in str(excinfo.value) or "08:00:00" in str(excinfo.value)


def test_editing_a_schedule_never_conflicts_with_itself(institution, existing_schedule):
    existing_schedule.start_time = time(8, 15)
    validate_schedule_conflict(existing_schedule)  # must not raise
