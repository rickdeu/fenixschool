"""Tests for the guardian portal's "Frequência" view (issue #69,
RF-FREQ-04): scoped automatically to the Guardian's own educando(s)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.attendance.models import Attendance
from apps.core.context import tenant_context
from apps.core.models import IdentificationDocumentType
from apps.enrollment.models import Guardian, Student, StudentGuardian
from apps.guardian_portal.services import SELECTED_STUDENT_SESSION_KEY

pytestmark = pytest.mark.django_db

URL = reverse("guardian_portal:attendance")
MONDAY = date(2026, 3, 2)


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


def _link(institution, student, guardian):
    return StudentGuardian.objects.create(
        institution=institution, origin_node_id=_origin(), student=student, guardian=guardian
    )


def test_requires_login(client):
    response = client.get(URL)

    assert response.status_code == 302


def test_shows_the_attendance_summary_for_the_selected_student(
    institution, document_type, enrollment, student, schedule, teacher
):
    user = User.objects.create_user(
        username="enc-freq",
        profile=Profile.GUARDIAN,
        institution=institution,
        password="senha-forte-123",
    )
    with tenant_context(institution.id):
        guardian = _make_guardian(institution, document_type, document_number="ENC-FREQ", user=user)
        _link(institution, student, guardian)
        for week in range(13):
            Attendance.objects.create(
                institution=institution,
                origin_node_id=_origin(),
                student=student,
                enrollment=enrollment,
                schedule=schedule,
                date=MONDAY + timedelta(days=7 * week),
                status=Attendance.Status.ABSENT,
                registered_by=teacher,
            )

    client = Client()
    client.login(username="enc-freq", password="senha-forte-123")
    session = client.session
    session[SELECTED_STUDENT_SESSION_KEY] = str(student.id)
    session.save()

    response = client.get(URL)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Assiduidade global" in content
    assert response.context["summary"]["unjustified_absence_hours"] == Decimal("13")


def test_never_shows_another_guardians_student(institution, document_type, enrollment, student):
    user = User.objects.create_user(
        username="enc-freq2",
        profile=Profile.GUARDIAN,
        institution=institution,
        password="senha-forte-123",
    )
    with tenant_context(institution.id):
        guardian = _make_guardian(
            institution, document_type, document_number="ENC-FREQ2", user=user
        )
        other_student = Student.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            first_name="Outro",
            last_name="Aluno",
            birth_date=date(2011, 1, 1),
            gender=Student.Gender.MALE,
            document_type=document_type,
            document_number="OTHER-999",
            document_issue_date=date(2020, 1, 1),
            document_issue_place="Nacional - Luanda",
            guardian_consent_given_by=guardian,
        )
        _link(institution, other_student, guardian)

    client = Client()
    client.login(username="enc-freq2", password="senha-forte-123")
    session = client.session
    session[SELECTED_STUDENT_SESSION_KEY] = str(student.id)  # not their own
    session.save()

    response = client.get(URL)

    assert response.status_code == 200
    # Not one of their own students -- `resolve_selected_student` falls
    # back to None (or the guardian's own single student), never leaking
    # `student`'s (someone else's) data.
    assert response.context["selected_student"] != student
