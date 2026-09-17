"""Tests for `apps/accounts/factories.py` and the shared `user_factory`/`institution`
fixtures in the repository's root `conftest.py` (issue #153)."""

import pytest

from apps.accounts.factories import UserFactory
from apps.accounts.models import Profile

pytestmark = pytest.mark.django_db


def test_user_factory_creates_a_usable_password():
    user = UserFactory()

    assert user.check_password("Test-Password-123")


def test_user_factory_default_profile_is_institution_admin():
    user = UserFactory()

    assert user.profile == Profile.INSTITUTION_ADMIN


def test_user_factory_sequence_produces_distinct_usernames():
    first = UserFactory()
    second = UserFactory()

    assert first.username != second.username


@pytest.mark.parametrize("profile", [choice.value for choice in Profile])
def test_user_factory_supports_every_profile(profile, institution):
    user = UserFactory(profile=profile, institution=institution)

    assert user.profile == profile


def test_shared_user_factory_fixture_binds_institution(user_factory, institution):
    user = user_factory(profile=Profile.TEACHER, institution=institution)

    assert user.institution == institution
    assert user.profile == Profile.TEACHER


def test_shared_user_factory_fixture_allows_no_institution_for_super_admin(user_factory):
    user = user_factory(profile=Profile.SUPER_ADMIN, institution=None)

    assert user.is_super_admin
    assert user.institution is None
