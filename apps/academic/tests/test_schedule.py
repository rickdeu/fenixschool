"""Tests for the Horário model (RF-CURR-06, docs/05-modelo-de-dados.md §5.10,
issue #36)."""

import uuid
from datetime import date, time

import pytest
from django.core.exceptions import ValidationError

from apps.academic.models import (
    Course,
    CurricularYear,
    Department,
    Room,
    Schedule,
    SchoolClass,
    Subject,
)
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, Institution

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
def room(institution):
    with tenant_context(institution.id):
        return Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=30
        )


@pytest.fixture
def teacher(institution):
    return User.objects.create_user(
        username="professor1", institution=institution, profile=Profile.TEACHER, password="x"
    )


def test_schedule_str(institution, school_class, subject, room, teacher):
    with tenant_context(institution.id):
        schedule = Schedule.objects.create(
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

    assert "10.ª A" in str(schedule)
    assert "Matemática" in str(schedule)
    assert "Segunda-feira" in str(schedule)


def test_end_time_must_be_after_start_time(institution, school_class, subject, room, teacher):
    with tenant_context(institution.id), pytest.raises(ValidationError):
        Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(9, 30),
            end_time=time(8, 0),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=teacher,
        )


def test_teacher_must_have_a_teaching_profile(institution, school_class, subject, room):
    non_teacher = User.objects.create_user(
        username="secretaria1",
        institution=institution,
        profile=Profile.SECRETARY,
        password="x",
    )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=non_teacher,
        )


def test_homeroom_teacher_profile_is_also_accepted(
    institution, school_class, subject, room
):
    homeroom_teacher = User.objects.create_user(
        username="director1",
        institution=institution,
        profile=Profile.HOMEROOM_TEACHER,
        password="x",
    )

    with tenant_context(institution.id):
        schedule = Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=room,
            teacher=homeroom_teacher,
        )

    assert schedule.teacher == homeroom_teacher


def test_subject_must_belong_to_the_school_classs_curricular_year(
    institution, department, cycle, academic_year
):
    with tenant_context(institution.id):
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
        year_1 = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=1,
            equivalent_grade="10.ª classe",
        )
        year_2 = CurricularYear.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            course=course,
            number=2,
            equivalent_grade="11.ª classe",
        )
        subject_of_year_2 = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT2",
            name="Matemática II",
            created_on=date(2020, 1, 1),
            course=course,
            curricular_year=year_2,
            cycle=cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )
        class_of_year_1 = SchoolClass.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="10A",
            designation="10.ª A",
            academic_year=academic_year,
            course=course,
            curricular_year=year_1,
            shift=SchoolClass.Shift.MORNING,
        )
        room_obj = Room.objects.create(
            institution=institution, origin_node_id=_origin(), designation="Sala 1", capacity=30
        )
        teacher_obj = User.objects.create_user(
            username="professor1", institution=institution, profile=Profile.TEACHER, password="x"
        )

        with pytest.raises(ValidationError):
            Schedule.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                school_class=class_of_year_1,
                subject=subject_of_year_2,
                weekday=Schedule.Weekday.MONDAY,
                start_time=time(8, 0),
                end_time=time(9, 30),
                regime=Schedule.Regime.THEORETICAL,
                room=room_obj,
                teacher=teacher_obj,
            )


def test_room_must_belong_to_the_same_institution(institution, school_class, subject, teacher):
    other_institution = Institution.objects.create(name="Outra Escola")
    with tenant_context(other_institution.id):
        foreign_room = Room.objects.create(
            institution=other_institution,
            origin_node_id=_origin(),
            designation="Sala Externa",
            capacity=20,
        )

    with tenant_context(institution.id), pytest.raises(ValidationError):
        Schedule.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            school_class=school_class,
            subject=subject,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(9, 30),
            regime=Schedule.Regime.THEORETICAL,
            room=foreign_room,
            teacher=teacher,
        )
