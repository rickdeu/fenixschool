"""Tests for the guardian portal's dashboard/student-selector view (issue #52,
RF-MAT-12)."""

import uuid
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian, Student, StudentGuardian
from apps.guardian_portal.services import SELECTED_STUDENT_SESSION_KEY

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


def test_requires_login(client):
    response = client.get(reverse("guardian_portal:dashboard"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_denies_a_non_guardian_profile(institution):
    User.objects.create_user(username="prof1", profile=Profile.TEACHER, password="pw12345")
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(reverse("guardian_portal:dashboard"))

    assert response.status_code == 403


def test_shows_a_message_when_no_students_are_linked(institution):
    User.objects.create_user(
        username="enc0", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    client = Client()
    client.login(username="enc0", password="pw12345")

    response = client.get(reverse("guardian_portal:dashboard"))

    assert response.status_code == 200
    assert "Não há nenhum educando associado" in response.content.decode()


def test_shows_the_single_student_directly_without_a_selector(institution, document_type):
    user = User.objects.create_user(
        username="enc1", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type, document_number="ENC-1", user=user)
        student = _make_student(institution, document_type, guardian, document_number="ALU-1")
        _link(institution, student, guardian)

    client = Client()
    client.login(username="enc1", password="pw12345")

    response = client.get(reverse("guardian_portal:dashboard"))

    content = response.content.decode()
    assert response.status_code == 200
    assert student.first_name in content
    assert response.context["selector_form"] is None


def test_shows_a_selector_when_more_than_one_student(institution, document_type):
    user = User.objects.create_user(
        username="enc2", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type, document_number="ENC-2", user=user)
        student_a = _make_student(institution, document_type, guardian, document_number="ALU-A")
        student_b = _make_student(institution, document_type, guardian, document_number="ALU-B")
        _link(institution, student_a, guardian)
        _link(institution, student_b, guardian)

    client = Client()
    client.login(username="enc2", password="pw12345")

    response = client.get(reverse("guardian_portal:dashboard"))

    assert response.status_code == 200
    assert response.context["selector_form"] is not None
    # RF-MAT-12: nothing chosen yet -- no student shown until picked.
    assert response.context["selected_student"] is None


def test_the_selector_switches_the_shown_student(institution, document_type):
    user = User.objects.create_user(
        username="enc3", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type, document_number="ENC-3", user=user)
        student_a = _make_student(institution, document_type, guardian, document_number="ALU-C")
        student_b = _make_student(institution, document_type, guardian, document_number="ALU-D")
        _link(institution, student_a, guardian)
        _link(institution, student_b, guardian)

    client = Client()
    client.login(username="enc3", password="pw12345")

    post_response = client.post(
        reverse("guardian_portal:dashboard"), {"student": str(student_b.id)}
    )
    assert post_response.status_code == 302
    assert client.session[SELECTED_STUDENT_SESSION_KEY] == str(student_b.id)

    get_response = client.get(reverse("guardian_portal:dashboard"))
    assert get_response.context["selected_student"] == student_b


def test_cannot_select_a_student_that_is_not_their_own(institution, document_type):
    """Security-critical: posting another guardian's student id must never
    let it become "selected" -- the selector's own choices are built from
    `get_own_students`, but a crafted POST could still send an arbitrary id."""
    user_a = User.objects.create_user(
        username="enc4", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    user_b = User.objects.create_user(
        username="enc5", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )
    with tenant_context(institution.id):
        guardian_a = _make_guardian(
            institution, document_type, document_number="ENC-4", user=user_a
        )
        guardian_b = _make_guardian(
            institution, document_type, document_number="ENC-5", user=user_b
        )
        student_a1 = _make_student(institution, document_type, guardian_a, document_number="ALU-E")
        student_a2 = _make_student(institution, document_type, guardian_a, document_number="ALU-F")
        other_student = _make_student(
            institution, document_type, guardian_b, document_number="ALU-G"
        )
        _link(institution, student_a1, guardian_a)
        _link(institution, student_a2, guardian_a)
        _link(institution, other_student, guardian_b)

    client = Client()
    client.login(username="enc4", password="pw12345")

    response = client.post(reverse("guardian_portal:dashboard"), {"student": str(other_student.id)})

    assert response.status_code == 200
    assert response.context["selector_form"].errors
    assert client.session.get(SELECTED_STUDENT_SESSION_KEY) is None


def test_login_redirects_a_guardian_straight_to_the_portal(institution, document_type):
    User.objects.create_user(
        username="enc6", profile=Profile.GUARDIAN, institution=institution, password="pw12345"
    )

    response = Client().post(reverse("accounts:login"), {"username": "enc6", "password": "pw12345"})

    assert response.status_code == 302
    assert response.url == reverse("guardian_portal:dashboard")
