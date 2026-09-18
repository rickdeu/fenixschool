"""Tests for automatic profile->group synchronisation (issue #113,
docs/07-perfis-permissoes-e-fluxos.md §7.2)."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import Profile, User
from apps.accounts.services import PROFILE_GROUP_NAMES

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(("profile", "group_name"), list(PROFILE_GROUP_NAMES.items()))
def test_creating_a_user_assigns_the_matching_group(profile, group_name):
    user = User.objects.create_user(username=f"user-{profile}", profile=profile)

    assert list(user.groups.values_list("name", flat=True)) == [group_name]


def test_changing_a_users_profile_updates_their_group():
    user = User.objects.create_user(username="joao", profile=Profile.TEACHER)
    assert list(user.groups.values_list("name", flat=True)) == ["Docente"]

    user.profile = Profile.SECRETARY
    user.save()

    assert list(user.groups.values_list("name", flat=True)) == ["Secretaria Escolar"]


def test_saving_without_changing_the_profile_does_not_touch_groups_needlessly():
    user = User.objects.create_user(username="maria", profile=Profile.TEACHER)
    group_ids_before = set(user.groups.values_list("pk", flat=True))

    user.first_name = "Maria"
    user.save()

    assert set(user.groups.values_list("pk", flat=True)) == group_ids_before


def test_an_extra_manually_granted_group_is_dropped_on_the_next_profile_driven_save():
    """`profile` is the single source of truth (issue #113) -- any group
    assigned outside of it (e.g. directly via the ORM/a script) doesn't
    survive the next save, by design."""
    user = User.objects.create_user(username="pedro", profile=Profile.TEACHER)
    user.groups.add(Group.objects.get(name="Biblioteca"))
    assert user.groups.count() == 2

    user.save()

    assert list(user.groups.values_list("name", flat=True)) == ["Docente"]
