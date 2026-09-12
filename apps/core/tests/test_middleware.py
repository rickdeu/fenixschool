"""Tests for `TenantMiddleware` (issue #5) -- see docs/04-arquitetura-tecnica.md §4.4.4."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore

from apps.accounts.models import Profile, User
from apps.core.context import get_current_institution
from apps.core.middleware import TenantMiddleware

pytestmark = pytest.mark.django_db


def _run_middleware(request, get_response=lambda req: req):
    return TenantMiddleware(get_response=get_response)(request)


def test_regular_user_gets_their_own_institution(rf, institution_factory):
    institution = institution_factory("Regular User's School")
    user = User.objects.create_user(
        username="teacher", password="x", profile=Profile.TEACHER, institution=institution
    )
    request = rf.get("/")
    request.user = user
    request.session = SessionStore()

    _run_middleware(request)

    assert request.institution == institution
    assert request.institution_id == institution.id


def test_super_admin_without_a_selection_has_no_institution(rf):
    user = User.objects.create_user(username="root", password="x", profile=Profile.SUPER_ADMIN)
    request = rf.get("/")
    request.user = user
    request.session = SessionStore()

    _run_middleware(request)

    assert request.institution is None
    assert request.institution_id is None


def test_super_admin_can_select_an_institution_to_view(rf, institution_factory):
    institution = institution_factory("Selected School")
    user = User.objects.create_user(username="root2", password="x", profile=Profile.SUPER_ADMIN)
    request = rf.get("/")
    request.user = user
    request.session = SessionStore()
    request.session[TenantMiddleware.SESSION_KEY] = str(institution.id)

    _run_middleware(request)

    assert request.institution == institution
    assert request.institution_id == institution.id


def test_anonymous_request_has_no_institution(rf):
    request = rf.get("/")
    request.user = AnonymousUser()

    _run_middleware(request)

    assert request.institution is None
    assert request.institution_id is None


def test_tenant_context_is_active_during_the_request_and_reset_afterwards(rf, institution_factory):
    institution = institution_factory()
    user = User.objects.create_user(
        username="teacher2", password="x", profile=Profile.TEACHER, institution=institution
    )
    request = rf.get("/")
    request.user = user
    request.session = SessionStore()

    seen_during_request = {}

    def get_response(req):
        seen_during_request["institution_id"] = get_current_institution()
        return req

    _run_middleware(request, get_response=get_response)

    assert seen_during_request["institution_id"] == institution.id
    assert get_current_institution() is None
