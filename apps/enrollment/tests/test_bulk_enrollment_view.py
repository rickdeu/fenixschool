"""Tests for the bulk Matrícula view (issue #241): enrolling every Student
admitted from a Candidate, for a given course, in one action."""

import uuid
from datetime import date

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.academic.models import Course, CurricularYear, Department, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import AcademicCycle, AcademicYear, IdentificationDocumentType
from apps.enrollment.models import Candidate, Enrollment, Guardian, Student

pytestmark = pytest.mark.django_db

URL = "/inscricoes/matriculas/lote/"


def _origin():
    return uuid.uuid4()


@pytest.fixture
def document_type(db):
    return IdentificationDocumentType.objects.get(code="bilhete-de-identidade")


@pytest.fixture
def secretary_client(institution):
    secretary = User.objects.create_user(
        username="secretaria1",
        institution=institution,
        profile=Profile.SECRETARY,
        password="senha-forte-123",
    )
    secretary.groups.add(Group.objects.get(name="Secretaria Escolar"))
    client = Client()
    client.login(username="secretaria1", password="senha-forte-123")
    return client


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
            max_enrollment=1,
        )
        guardian = Guardian.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name="Encarregado",
            kinship=Guardian.Kinship.MOTHER,
            document_type=document_type,
            document_number="ENC-1",
        )
    return {
        "course": course,
        "school_class": school_class,
        "guardian": guardian,
    }


def _admitted_student(institution, document_type, guardian, course, *, name, number):
    with tenant_context(institution.id):
        candidate = Candidate.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            full_name=name,
            birth_date=date(2012, 4, 10),
            document_type=document_type,
            document_number=f"DOC-{number}",
            document_expiry_date=date(2030, 1, 1),
            desired_course=course,
            contact="923000000",
            status=Candidate.Status.ADMITTED,
        )
        first_name, _, last_name = name.partition(" ")
        return Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name=first_name,
            last_name=last_name,
            birth_date=date(2012, 4, 10),
            gender=Student.Gender.FEMALE,
            document_type=document_type,
            document_number=f"DOC-{number}",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
            admitted_from_candidate=candidate,
        )


def test_unauthenticated_user_is_redirected_to_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_user_without_permission_is_forbidden(institution):
    User.objects.create_user(
        username="aluno1", institution=institution, profile=Profile.STUDENT, password="x"
    )
    client = Client()
    client.login(username="aluno1", password="x")

    response = client.get(URL)

    assert response.status_code == 403


def test_submitting_the_course_filter_without_choosing_one_does_not_crash(secretary_client):
    """Clicking "Ver" with the blank "Escolha um curso" option selected posts
    `?course=` (an empty string), not a missing param -- `Course.objects.filter(pk="")`
    used to raise a `ValidationError` ("not a valid UUID") instead of just
    finding nothing, crashing the whole page with a 500 (found in manual
    verification via Docker)."""
    response = secretary_client.get(URL, {"course": ""})

    assert response.status_code == 200
    assert response.context["course"] is None


def test_submitting_without_choosing_a_turma_does_not_crash(secretary_client, class_setup):
    """Same bug class as above, on the turma dropdown: the "Nenhuma turma
    configurada" placeholder option also posts an empty string."""
    response = secretary_client.post(
        URL,
        {"course": str(class_setup["course"].pk), "school_class": "", "student_ids": []},
    )

    assert response.status_code == 200


def test_lists_only_admitted_students_not_yet_enrolled_for_the_chosen_course(
    secretary_client, institution, document_type, class_setup
):
    eligible = _admitted_student(
        institution, document_type, class_setup["guardian"], class_setup["course"],
        name="Yolene Hangalo", number="1",
    )
    # A walk-in Student (no candidate origin) must never show up here.
    with tenant_context(institution.id):
        Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Zeca",
            last_name="Neto",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="DOC-walkin",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=class_setup["guardian"],
        )

    response = secretary_client.get(URL, {"course": str(class_setup["course"].pk)})

    assert response.status_code == 200
    assert list(response.context["eligible_students"]) == [eligible]


def test_bulk_enrolling_selected_students_creates_enrollments(
    secretary_client, institution, document_type, class_setup
):
    student = _admitted_student(
        institution, document_type, class_setup["guardian"], class_setup["course"],
        name="Yolene Hangalo", number="1",
    )

    response = secretary_client.post(
        URL,
        {
            "course": str(class_setup["course"].pk),
            "school_class": str(class_setup["school_class"].pk),
            "student_ids": [str(student.pk)],
        },
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        enrollment = Enrollment.objects.get(student=student)
    assert enrollment.school_class == class_setup["school_class"]
    assert enrollment.presented_document_number == student.document_number


def test_bulk_enrolling_stops_once_the_class_is_full(
    secretary_client, institution, document_type, class_setup
):
    """`class_setup`'s school_class has `max_enrollment=1`."""
    first = _admitted_student(
        institution, document_type, class_setup["guardian"], class_setup["course"],
        name="Yolene Hangalo", number="1",
    )
    second = _admitted_student(
        institution, document_type, class_setup["guardian"], class_setup["course"],
        name="Ana Kavungo", number="2",
    )

    response = secretary_client.post(
        URL,
        {
            "course": str(class_setup["course"].pk),
            "school_class": str(class_setup["school_class"].pk),
            "student_ids": [str(first.pk), str(second.pk)],
        },
    )

    assert response.status_code == 200
    with tenant_context(institution.id):
        assert Enrollment.objects.filter(student__in=[first, second]).count() == 1


def test_students_already_enrolled_are_not_offered_again(
    secretary_client, institution, document_type, class_setup
):
    student = _admitted_student(
        institution, document_type, class_setup["guardian"], class_setup["course"],
        name="Yolene Hangalo", number="1",
    )
    secretary_client.post(
        URL,
        {
            "course": str(class_setup["course"].pk),
            "school_class": str(class_setup["school_class"].pk),
            "student_ids": [str(student.pk)],
        },
    )

    response = secretary_client.get(URL, {"course": str(class_setup["course"].pk)})

    assert list(response.context["eligible_students"]) == []
