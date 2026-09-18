"""Tests for the automatic audit-log signals (issue #140, RNF-AUD-01)."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import Profile, User
from apps.audit.context import audit_actor_context
from apps.audit.models import AuditLogEntry
from apps.core.context import tenant_context

pytestmark = pytest.mark.django_db


def _origin():
    return uuid.uuid4()


def _entries_for(instance):
    return AuditLogEntry.objects.filter(entity=instance._meta.label, entity_id=str(instance.pk))


# -- accounts.User --------------------------------------------------------


def test_creating_a_user_records_a_create_entry():
    admin = User.objects.create_user(username="admin1", profile=Profile.INSTITUTION_ADMIN)

    with audit_actor_context(admin, "10.0.0.1"):
        user = User.objects.create_user(username="joao", profile=Profile.TEACHER)

    # 2 entries, not 1: creation itself, plus the automatic profile->group
    # sync (issue #113) it triggers -- a brand new user starts in no
    # groups at all, so it's a real, distinct "Permissão" change worth its
    # own entry, not a side effect to suppress.
    entry = _entries_for(user).get(action=AuditLogEntry.Action.CREATE)
    assert entry.user == admin
    assert entry.ip_address == "10.0.0.1"
    assert entry.values_after["username"] == "joao"


def test_password_is_never_captured_in_a_users_audit_trail():
    user = User.objects.create_user(
        username="joao2", profile=Profile.TEACHER, password="secret-123"
    )

    entry = _entries_for(user).get(action=AuditLogEntry.Action.CREATE)

    assert "password" not in entry.values_after
    assert "password" not in entry.values_before


def test_updating_a_user_records_an_update_entry_with_before_and_after():
    user = User.objects.create_user(username="joao3", profile=Profile.TEACHER, first_name="Joao")

    user.first_name = "João"
    user.save()

    # `.exclude(...)`: creation itself also triggers an UPDATE entry for its
    # own automatic profile->group sync (issue #113) -- this test is about
    # the *field* change, not that one.
    entry = (
        _entries_for(user)
        .filter(action=AuditLogEntry.Action.UPDATE)
        .exclude(values_after__has_key="groups_changed")
        .get()
    )
    assert entry.values_before["first_name"] == "Joao"
    assert entry.values_after["first_name"] == "João"


def test_saving_a_user_without_any_real_change_records_nothing_new():
    user = User.objects.create_user(username="joao4", profile=Profile.TEACHER)
    count_after_create = _entries_for(user).count()

    user.save()

    assert _entries_for(user).count() == count_after_create


def test_deleting_a_user_records_a_delete_entry():
    user = User.objects.create_user(username="joao5", profile=Profile.TEACHER)
    user_pk = user.pk

    user.delete()

    entries = AuditLogEntry.objects.filter(entity="accounts.User", entity_id=str(user_pk))
    assert entries.filter(action=AuditLogEntry.Action.DELETE).exists()


def test_changing_a_users_groups_records_an_update_entry():
    # A profile of "Docente" already auto-syncs the "Docente" group on
    # creation (issue #113) -- adding a *different* group here (Diretor de
    # Turma, on top of it) is what actually exercises "a new group being
    # added", rather than a no-op re-add of one already there.
    user = User.objects.create_user(username="joao6", profile=Profile.TEACHER)
    group = Group.objects.get(name="Diretor de Turma")

    user.groups.add(group)

    entry = _entries_for(user).filter(values_after__groups_changed="post_add").latest("timestamp")
    assert entry.action == AuditLogEntry.Action.UPDATE
    assert str(group.pk) in entry.values_after["group_ids"]


def test_no_actor_in_context_records_a_userless_entry():
    """A management command or other system task with no request/actor
    context still gets an entry -- just without a `user`, per RNF-AUD-01's
    own field being nullable for exactly this case."""
    user = User.objects.create_user(username="joao7", profile=Profile.TEACHER)

    entry = _entries_for(user).get(action=AuditLogEntry.Action.CREATE)
    assert entry.user is None


# -- enrollment.Enrollment -------------------------------------------------


@pytest.fixture
def enrollment_setup(institution):
    from apps.academic.models import Course, CurricularYear, Department, SchoolClass
    from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
    from apps.enrollment.models import Enrollment, Guardian, Student

    with tenant_context(institution.id):
        document_type = IdentificationDocumentType.objects.get(code="bilhete-de-identidade")
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
            first_name="Aluno",
            last_name="Teste",
            birth_date=date(2010, 1, 1),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number="ALU-1",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Luanda",
            guardian_consent_given_by=guardian,
        )
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
        enrollment = Enrollment.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=student,
            school_class=school_class,
            course=course,
            academic_year=academic_year,
            cycle=cycle,
            curricular_year=curricular_year,
            presented_document_type=document_type,
            presented_document_number="ALU-1-DOC",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
        )
    return enrollment


def test_creating_an_enrollment_records_a_create_entry(institution, enrollment_setup):
    entry = _entries_for(enrollment_setup).get(action=AuditLogEntry.Action.CREATE)

    assert entry.values_after["student"] == str(enrollment_setup.student_id)


def test_soft_deleting_an_enrollment_records_a_delete_entry_not_an_update(
    institution, enrollment_setup
):
    with tenant_context(institution.id):
        enrollment_setup.is_deleted = True
        enrollment_setup.save(update_fields=["is_deleted"])

    entry = _entries_for(enrollment_setup).latest("timestamp")
    assert entry.action == AuditLogEntry.Action.DELETE


# -- grading.Grade / grading.FinalGrade -------------------------------------


@pytest.fixture
def grade_setup(institution, enrollment_setup):
    from apps.academic.models import Subject
    from apps.core.models import AcademicTerm
    from apps.grading.models import EvaluationType
    from apps.grading.services import set_institution_default_formula

    with tenant_context(institution.id):
        subject = Subject.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            code="MAT",
            name="Matemática",
            created_on=date(2020, 1, 1),
            course=enrollment_setup.course,
            curricular_year=enrollment_setup.curricular_year,
            cycle=enrollment_setup.cycle,
            subject_type=Subject.SubjectType.MANDATORY,
            weekly_hours=4,
        )
        evaluation_type = EvaluationType.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            name="MAC",
            default_weight="1",
        )
        set_institution_default_formula(institution, {"MAC": 1})
        academic_term = AcademicTerm.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            academic_year=enrollment_setup.academic_year,
            number=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 5, 31),
        )
        teacher = User.objects.create_user(
            username="professor-audit", institution=institution, profile=Profile.TEACHER
        )
    return {
        "subject": subject,
        "evaluation_type": evaluation_type,
        "academic_term": academic_term,
        "teacher": teacher,
    }


def test_creating_a_grade_records_a_create_entry(institution, enrollment_setup, grade_setup):
    from apps.grading.models import Grade

    with tenant_context(institution.id):
        grade = Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment_setup.student,
            enrollment=enrollment_setup,
            subject=grade_setup["subject"],
            academic_term=grade_setup["academic_term"],
            evaluation_type=grade_setup["evaluation_type"],
            value="15",
            teacher=grade_setup["teacher"],
        )

    entry = _entries_for(grade).get(action=AuditLogEntry.Action.CREATE)
    assert entry.values_after["value"] == "15"


def test_manually_overriding_a_final_grade_records_the_reason_in_the_audit_diff(
    institution, enrollment_setup, grade_setup
):
    from apps.grading.models import Grade
    from apps.grading.services import ajustar_media_manualmente, registar_media_final

    with tenant_context(institution.id):
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment_setup.student,
            enrollment=enrollment_setup,
            subject=grade_setup["subject"],
            academic_term=grade_setup["academic_term"],
            evaluation_type=grade_setup["evaluation_type"],
            value="10",
            teacher=grade_setup["teacher"],
        )
        final_grade = registar_media_final(
            enrollment=enrollment_setup,
            subject=grade_setup["subject"],
            academic_term=grade_setup["academic_term"],
            origin_node_id=_origin(),
        )

        ajustar_media_manualmente(
            final_grade=final_grade,
            user=grade_setup["teacher"],
            value="16",
            reason="Trabalho de recuperação avaliado.",
        )

    entry = _entries_for(final_grade).filter(action=AuditLogEntry.Action.UPDATE).latest("timestamp")
    assert entry.values_after["override_reason"] == "Trabalho de recuperação avaliado."
    assert entry.values_after["manual_override_value"] == "16"
