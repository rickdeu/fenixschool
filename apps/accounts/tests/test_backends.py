"""Tests for `EmailOrPhoneBackend` (issue #24, docs/09-seguranca-e-privacidade.md §9.2)."""

import pytest
from django.contrib.auth import authenticate

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="joao",
        email="joao@escola.ao",
        phone="923000000",
        password="senha-forte-123",
    )


def test_authenticates_by_email(user):
    authenticated = authenticate(username="joao@escola.ao", password="senha-forte-123")

    assert authenticated == user


def test_authenticates_by_email_case_insensitively(user):
    authenticated = authenticate(username="JOAO@ESCOLA.AO", password="senha-forte-123")

    assert authenticated == user


def test_authenticates_by_phone(user):
    authenticated = authenticate(username="923000000", password="senha-forte-123")

    assert authenticated == user


def test_rejects_wrong_password(user):
    assert authenticate(username="joao@escola.ao", password="wrong") is None


def test_rejects_unknown_identifier():
    assert authenticate(username="ninguem@escola.ao", password="whatever") is None


def test_rejects_inactive_user(user):
    user.is_active = False
    user.save()

    assert authenticate(username="joao@escola.ao", password="senha-forte-123") is None


def test_does_not_crash_on_duplicate_email(user):
    User.objects.create_user(username="maria", email="joao@escola.ao", password="outra-senha-123")

    # Ambiguous identifier -- fails closed (no login) rather than guessing
    # which of the two accounts was meant.
    assert authenticate(username="joao@escola.ao", password="senha-forte-123") is None
