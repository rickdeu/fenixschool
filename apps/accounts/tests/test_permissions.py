"""Tests for `apps.accounts.permissions.require_profile` -- the shared
"<perfil>_required" decorator factory (used by
`apps.grading.permissions.docente_required`/
`apps.guardian_portal.permissions.guardian_required`)."""

import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory

from apps.accounts.models import Profile, User
from apps.accounts.permissions import require_profile

pytestmark = pytest.mark.django_db


@require_profile(Profile.TEACHER, Profile.HOMEROOM_TEACHER)
def _protected_view(request):
    return HttpResponse("ok")


def test_allows_a_user_with_the_required_profile():
    user = User.objects.create_user(username="prof1", profile=Profile.TEACHER)
    request = RequestFactory().get("/")
    request.user = user

    response = _protected_view(request)

    assert response.status_code == 200


def test_denies_a_user_with_a_different_profile():
    user = User.objects.create_user(username="sec1", profile=Profile.SECRETARY)
    request = RequestFactory().get("/")
    request.user = user

    with pytest.raises(PermissionDenied):
        _protected_view(request)


def test_super_admin_always_bypasses_the_profile_check():
    """"Super Administrador deve ter acesso a tudo, sem restrição alguma"."""
    super_admin = User.objects.create_user(username="root1", profile=Profile.SUPER_ADMIN)
    assert super_admin.is_superuser is True  # sanity: the accounts-level guarantee held

    request = RequestFactory().get("/")
    request.user = super_admin

    response = _protected_view(request)

    assert response.status_code == 200
