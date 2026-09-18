"""A Super Administrator has no `institution` of their own until they pick one
to view (`apps.core.middleware.TenantMiddleware`) -- every institution-scoped
enrollment view must redirect gracefully instead of crashing on it. Found via
manual Docker verification: submitting the Inscrição form while logged in as
a Super Administrator raised an `IntegrityError` (`institution_id` NULL on
`Guardian`) instead of a friendly redirect, mirroring the bug
`apps.admin_panel`'s `test_config_view_redirects_gracefully_without_a_selected_institution`
(issue #18) already covers for the grading-formula views.
"""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def super_admin_client(verify_two_factor):
    super_admin = User.objects.create_user(
        username="superadmin1", profile=Profile.SUPER_ADMIN, password="pw12345", is_superuser=True
    )
    client = Client()
    client.login(username="superadmin1", password="pw12345")
    verify_two_factor(client, super_admin)
    return client


def test_student_search_redirects_gracefully_without_a_selected_institution(super_admin_client):
    response = super_admin_client.get(reverse("enrollment:student_search"), follow=True)

    assert response.status_code == 200
    assert response.redirect_chain
    assert "nenhuma instituição está seleccionada" in response.content.decode()


def test_student_inscription_redirects_gracefully_without_a_selected_institution(
    super_admin_client,
):
    response = super_admin_client.get(reverse("enrollment:student_inscription"), follow=True)

    assert response.status_code == 200
    assert response.redirect_chain
    assert "nenhuma instituição está seleccionada" in response.content.decode()


def test_student_inscription_post_never_reaches_the_database_without_an_institution(
    super_admin_client,
):
    """The regression itself: a POST used to reach `Guardian.save()` with no
    institution set at all, instead of being redirected away first."""
    response = super_admin_client.post(
        reverse("enrollment:student_inscription"), data={}, follow=True
    )

    assert response.status_code == 200
    assert response.redirect_chain
    assert "nenhuma instituição está seleccionada" in response.content.decode()


def test_enrollment_create_redirects_gracefully_without_a_selected_institution(
    super_admin_client,
):
    response = super_admin_client.get(
        reverse("enrollment:enrollment_create", args=[uuid.uuid4()]), follow=True
    )

    assert response.status_code == 200
    assert response.redirect_chain
    assert "nenhuma instituição está seleccionada" in response.content.decode()
