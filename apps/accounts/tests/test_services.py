"""Tests for `apps/accounts/services.py::create_user` (issue #23,
docs/04-arquitetura-tecnica.md §4.4.1)."""

import pytest

from apps.accounts.models import Profile, User
from apps.accounts.services import create_user

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "profile",
    [
        Profile.SECRETARY,
        Profile.TEACHER,
        Profile.HR,
        Profile.FINANCE,
    ],
)
def test_staff_created_by_the_institution_manager_inherit_their_institution(institution, profile):
    manager = User.objects.create_user(
        username="gestor",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
    )

    staff = create_user(
        created_by=manager,
        username=f"user-{profile}",
        profile=profile,
    )

    assert staff.institution == institution
    assert staff.created_by == manager


def test_explicit_institution_is_ignored_when_creator_is_not_a_super_admin(institution):
    manager = User.objects.create_user(
        username="gestor",
        institution=institution,
        profile=Profile.INSTITUTION_ADMIN,
    )
    another_institution = type(institution).objects.create(name="Another School")

    staff = create_user(
        created_by=manager,
        institution=another_institution,
        username="secretaria",
        profile=Profile.SECRETARY,
    )

    assert staff.institution == manager.institution
    assert staff.institution != another_institution


def test_only_a_super_admin_may_choose_the_institution_explicitly(institution):
    super_admin = User.objects.create_user(
        username="root", profile=Profile.SUPER_ADMIN, institution=None
    )

    manager = create_user(
        created_by=super_admin,
        institution=institution,
        username="gestor",
        profile=Profile.INSTITUTION_ADMIN,
    )

    assert manager.institution == institution
    assert manager.created_by == super_admin


def test_super_admin_must_provide_an_institution():
    super_admin = User.objects.create_user(
        username="root", profile=Profile.SUPER_ADMIN, institution=None
    )

    with pytest.raises(ValueError):
        create_user(created_by=super_admin, username="gestor", profile=Profile.INSTITUTION_ADMIN)
