"""Tests for `FinalGradeAdmin`'s manual-override flow (issue #58, RF-AVAL-02).

Goes through the real Django Admin change view (not a bare
`FinalGradeAdminForm(...)` instantiation), same reasoning as
`apps.academic.tests.test_forms`: `ModelAdmin.get_form()` rebuilds
`ModelChoiceField` querysets fresh, inside the request's own tenant context.
"""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User
from apps.core.context import tenant_context
from apps.grading.models import Grade
from apps.grading.services import registar_media_final, set_institution_default_formula

pytestmark = pytest.mark.django_db


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
def final_grade(institution, enrollment, subject, evaluation_type, academic_term, teacher):
    with tenant_context(institution.id):
        set_institution_default_formula(institution, {evaluation_type.name: Decimal("1")})
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("10"),
            teacher=teacher,
        )
        return registar_media_final(
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            origin_node_id=_origin(),
        )


def _change_url(final_grade):
    return reverse("admin:grading_finalgrade_change", args=[final_grade.pk])


def _form_data(institution, final_grade, **overrides):
    data = {
        "institution": str(institution.pk),
        "enrollment": str(final_grade.enrollment_id),
        "subject": str(final_grade.subject_id),
        "academic_term": str(final_grade.academic_term_id),
        "manual_override_value": "",
        "override_reason": "",
        "origin_node_id": str(final_grade.origin_node_id),
        "version": str(final_grade.version),
    }
    data.update(overrides)
    return data


def test_add_view_is_disabled(admin_client):
    response = admin_client.get(reverse("admin:grading_finalgrade_add"))

    assert response.status_code == 403


def test_final_grade_changelist_does_not_explode_into_a_recursive_select_related(
    admin_client, final_grade
):
    """Regression test: `list_display` on `FinalGradeAdmin`/`GradeAdmin` is
    almost entirely FK columns, which makes Django's Admin auto-apply a
    *bare* `select_related()` (recursive, follows every non-null FK at
    every level) whenever `list_select_related` is left at its default.
    Combined with this app's dense FK graph (every related model is itself
    a `SyncedModel` with its own `institution` FK), that produced a single
    changelist query joining `core_institution` 30+ times over -- enough to
    hit SQLite's 64-table join limit outright. Fixed by giving both Admins
    an explicit, shallow `list_select_related`."""
    response = admin_client.get(reverse("admin:grading_finalgrade_changelist"))

    assert response.status_code == 200


def test_grade_changelist_does_not_explode_into_a_recursive_select_related(
    admin_client, institution, enrollment, subject, evaluation_type, academic_term, teacher
):
    with tenant_context(institution.id):
        Grade.objects.create(
            institution=institution,
            origin_node_id=_origin(),
            student=enrollment.student,
            enrollment=enrollment,
            subject=subject,
            academic_term=academic_term,
            evaluation_type=evaluation_type,
            value=Decimal("10"),
            teacher=teacher,
        )

    response = admin_client.get(reverse("admin:grading_grade_changelist"))

    assert response.status_code == 200


def test_manual_override_with_a_reason_is_accepted(admin_client, institution, final_grade):
    response = admin_client.post(
        _change_url(final_grade),
        _form_data(
            institution,
            final_grade,
            manual_override_value="16",
            override_reason="Recurso avaliado presencialmente.",
        ),
    )

    assert response.status_code == 302  # redirects on a successful save
    final_grade.refresh_from_db()
    assert final_grade.manual_override_value == Decimal("16.00")
    assert final_grade.override_reason == "Recurso avaliado presencialmente."
    assert final_grade.overridden_at is not None

    with tenant_context(institution.id):
        final_grade.refresh_from_db()
    assert final_grade.overridden_by is not None
    assert final_grade.overridden_by.username == "admin1"


def test_manual_override_without_a_reason_is_rejected(admin_client, institution, final_grade):
    response = admin_client.post(
        _change_url(final_grade),
        _form_data(institution, final_grade, manual_override_value="16", override_reason=""),
    )

    assert response.status_code == 200  # redisplays the form with an error
    assert "justifica" in response.content.decode().lower()

    final_grade.refresh_from_db()
    assert final_grade.manual_override_value is None
