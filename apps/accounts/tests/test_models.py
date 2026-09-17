"""Tests for `accounts.User`'s own fields (issue #21, docs/05-modelo-de-dados.md §5.24)."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

from apps.accounts.admin import CustomUserAdmin
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_new_user_gets_the_documented_field_defaults():
    user = User.objects.create_user(username="jose")

    assert user.phone == ""
    assert user.preferred_language == "pt"
    assert user.is_2fa_active is False


def test_preferred_language_accepts_every_configured_language():
    for code, _label in User._meta.get_field("preferred_language").choices:
        user = User(username=f"user-{code}", preferred_language=code)
        user.full_clean(exclude=["password"])


def test_auth_user_model_points_at_this_model():
    assert get_user_model() is User


def test_createsuperuser_produces_a_working_superuser():
    """Issue #21's acceptance criterion: "Migração inicial testada com createsuperuser"."""
    user = User.objects.create_superuser(username="root", password="a-strong-password-123")

    assert user.is_staff
    assert user.is_superuser
    assert user.check_password("a-strong-password-123")


def test_institution_is_editable_only_when_creating_a_user():
    admin_instance = CustomUserAdmin(User, admin.site)

    assert "institution" not in admin_instance.get_readonly_fields(request=None, obj=None)


def test_institution_is_read_only_once_a_user_already_exists(institution):
    user = User.objects.create_user(username="jose", institution=institution)
    admin_instance = CustomUserAdmin(User, admin.site)

    assert "institution" in admin_instance.get_readonly_fields(request=None, obj=user)
