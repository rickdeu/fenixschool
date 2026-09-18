"""Tests for `PreferredLanguageMiddleware` (issue #149, RNF-LOC-06/07)."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import translation

from apps.accounts.middleware import PreferredLanguageMiddleware
from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def _run_middleware(request, get_response=lambda req: req):
    return PreferredLanguageMiddleware(get_response=get_response)(request)


def test_activates_the_authenticated_users_preferred_language(rf):
    user = User.objects.create_user(
        username="joao", password="x", profile=Profile.TEACHER, preferred_language="umb"
    )
    request = rf.get("/")
    request.user = user

    seen = {}

    def get_response(req):
        seen["language"] = translation.get_language()
        seen["request_language_code"] = req.LANGUAGE_CODE
        return req

    _run_middleware(request, get_response=get_response)

    assert seen["language"] == "umb"
    assert seen["request_language_code"] == "umb"


def test_anonymous_request_defaults_to_pt_never_the_browser(rf):
    # Accept-Language deliberately asks for something else -- must be
    # ignored entirely (RNF-LOC-06/07's "nunca pelo browser").
    request = rf.get("/", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")
    request.user = AnonymousUser()

    seen = {}

    def get_response(req):
        seen["language"] = translation.get_language()
        return req

    _run_middleware(request, get_response=get_response)

    assert seen["language"] == "pt"


def test_authenticated_users_browser_language_is_also_ignored(rf):
    user = User.objects.create_user(
        username="maria", password="x", profile=Profile.TEACHER, preferred_language="kmb"
    )
    request = rf.get("/", HTTP_ACCEPT_LANGUAGE="fr-FR")
    request.user = user

    seen = {}

    def get_response(req):
        seen["language"] = translation.get_language()
        return req

    _run_middleware(request, get_response=get_response)

    assert seen["language"] == "kmb"


def test_deactivates_translation_after_the_request(rf):
    translation.activate("umb")

    request_user = User.objects.create_user(
        username="pedro", password="x", profile=Profile.TEACHER, preferred_language="kon"
    )
    request = rf.get("/")
    request.user = request_user

    _run_middleware(request)

    # deactivate() restores the "no override active" state rather than any
    # specific language -- get_language() then falls back to LANGUAGE_CODE.
    assert translation.get_language() == "pt"
