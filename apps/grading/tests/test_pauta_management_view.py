"""Tests for the "Pautas" list screen (issue #60, RF-AVAL-04) -- the real
admin_panel-style replacement for the old Django Admin homologar/reabrir
actions (Django Admin is never used by real users). Viewing/editing/
homologating a specific pauta is `test_pauta_detail_view.py`."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import Grade

pytestmark = pytest.mark.django_db

URL = reverse("grading:pauta_management")


def _origin():
    return uuid.uuid4()


@pytest.fixture
def admin_client(institution, verify_two_factor):
    admin = User.objects.create_user(
        username="admin1",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    admin.groups.add(Group.objects.get(name="Administrador da Instituição"))
    client = Client()
    client.login(username="admin1", password="senha-forte-123")
    verify_two_factor(client, admin)
    return client


@pytest.fixture
def grade(institution, enrollment, subject, evaluation_type, academic_term, teacher):
    with tenant_context(institution.id):
        return Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("15"),
            teacher=teacher,
        )


def test_non_privileged_profile_is_forbidden(institution, user_factory):
    teacher_only = user_factory(profile=Profile.TEACHER, institution=institution)
    client = Client()
    client.force_login(teacher_only)

    response = client.get(URL)

    assert response.status_code == 403


def test_selection_form_renders_without_a_query(admin_client):
    response = admin_client.get(URL)

    assert response.status_code == 200
    assert "rows" not in response.context


def test_lists_existing_occurrences(admin_client, grade, school_class, subject, evaluation_type):
    response = admin_client.get(URL)

    assert response.status_code == 200
    occurrences = response.context["occurrences"]
    assert len(occurrences) == 1
    assert occurrences[0]["school_class_id"] == school_class.id
    assert occurrences[0]["subject_id"] == subject.id
    assert occurrences[0]["total"] == 1
    assert occurrences[0]["is_closed"] is False
    content = response.content.decode()
    assert school_class.designation in content
    assert subject.name in content
