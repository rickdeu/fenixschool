"""Tests for 2FA/TOTP (issue #25, RNF-SEC-05, docs/09-seguranca-e-privacidade.md §9.2)."""

import time

import pytest
from django.test import Client
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import Profile, User
from apps.accounts.services import (
    get_two_factor_redirect_url_name,
    requires_two_factor,
    user_has_confirmed_totp_device,
)

pytestmark = pytest.mark.django_db


def _current_token(device: TOTPDevice) -> str:
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time()
    return str(totp.token()).zfill(device.digits)


# -- apps.accounts.services ---------------------------------------------------


@pytest.mark.parametrize(
    "profile", [Profile.SUPER_ADMIN, Profile.INSTITUTION_ADMIN, Profile.FINANCE]
)
def test_requires_two_factor_for_the_3_high_risk_profiles(profile):
    assert requires_two_factor(User(profile=profile)) is True


@pytest.mark.parametrize(
    "profile", [Profile.TEACHER, Profile.SECRETARY, Profile.STUDENT, Profile.GUARDIAN]
)
def test_does_not_require_two_factor_for_other_profiles(profile):
    assert requires_two_factor(User(profile=profile)) is False


def test_redirect_target_is_setup_when_there_is_no_confirmed_device():
    user = User.objects.create_user(username="fin1", profile=Profile.FINANCE, password="x")

    assert get_two_factor_redirect_url_name(user) == "accounts:two_factor_setup"
    assert user_has_confirmed_totp_device(user) is False


def test_redirect_target_is_verify_once_a_device_is_confirmed():
    user = User.objects.create_user(username="fin2", profile=Profile.FINANCE, password="x")
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)

    assert get_two_factor_redirect_url_name(user) == "accounts:two_factor_verify"
    assert user_has_confirmed_totp_device(user) is True


# -- RequireTwoFactorMiddleware, end-to-end ------------------------------------


def test_a_mandatory_profile_is_blocked_from_every_page_until_2fa_is_done():
    User.objects.create_user(
        username="admin1", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    client = Client()
    client.login(username="admin1", password="pw12345")

    response = client.get(reverse("accounts:landing_placeholder"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:two_factor_setup")


def test_an_optional_profile_is_never_redirected_to_2fa():
    User.objects.create_user(username="prof1", profile=Profile.TEACHER, password="pw12345")
    client = Client()
    client.login(username="prof1", password="pw12345")

    response = client.get(reverse("accounts:landing_placeholder"))

    assert response.status_code == 200


def test_a_returning_user_with_a_confirmed_device_is_sent_to_verify_not_setup():
    user = User.objects.create_user(
        username="admin2", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = Client()
    client.login(username="admin2", password="pw12345")

    response = client.get(reverse("accounts:landing_placeholder"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:two_factor_verify")


def test_login_itself_is_reachable_even_though_it_would_otherwise_be_blocked(client):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200


# -- two_factor_setup_view -----------------------------------------------------


def test_setup_view_renders_a_qr_code_and_a_manual_entry_key():
    User.objects.create_user(
        username="admin3", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    client = Client()
    client.login(username="admin3", password="pw12345")

    response = client.get(reverse("accounts:two_factor_setup"))

    assert response.status_code == 200
    assert "data:image/png;base64," in response.content.decode()
    assert response.context["manual_entry_key"]


def test_setup_view_confirms_the_device_and_completes_login_on_a_correct_code():
    user = User.objects.create_user(
        username="admin4", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    client = Client()
    client.login(username="admin4", password="pw12345")
    # GET first -- creates the pending (unconfirmed) device to scan.
    client.get(reverse("accounts:two_factor_setup"))
    device = TOTPDevice.objects.get(user=user, confirmed=False)

    response = client.post(
        reverse("accounts:two_factor_setup"), {"token": _current_token(device)}
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")
    device.refresh_from_db()
    assert device.confirmed is True
    # Verified now -- the very next request isn't bounced back to 2FA.
    landing = client.get(reverse("accounts:landing_placeholder"))
    assert landing.status_code == 200


def test_setup_view_rejects_an_incorrect_code_without_confirming_the_device():
    user = User.objects.create_user(
        username="admin5", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    client = Client()
    client.login(username="admin5", password="pw12345")
    client.get(reverse("accounts:two_factor_setup"))

    response = client.post(reverse("accounts:two_factor_setup"), {"token": "000000"})

    assert response.status_code == 200
    assert "Código inválido" in response.content.decode()
    assert not TOTPDevice.objects.filter(user=user, confirmed=True).exists()


# -- two_factor_verify_view -----------------------------------------------------


def test_verify_view_redirects_to_setup_when_there_is_no_confirmed_device():
    User.objects.create_user(
        username="admin6", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    client = Client()
    client.login(username="admin6", password="pw12345")

    response = client.get(reverse("accounts:two_factor_verify"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:two_factor_setup")


def test_verify_view_completes_login_on_a_correct_code():
    user = User.objects.create_user(
        username="admin7", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = Client()
    client.login(username="admin7", password="pw12345")

    response = client.post(
        reverse("accounts:two_factor_verify"), {"token": _current_token(device)}
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")


def test_verify_view_rejects_an_incorrect_code():
    user = User.objects.create_user(
        username="admin8", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = Client()
    client.login(username="admin8", password="pw12345")

    response = client.post(reverse("accounts:two_factor_verify"), {"token": "000000"})

    assert response.status_code == 200
    assert "Código inválido" in response.content.decode()


def test_totp_is_verifiable_with_no_external_service_call():
    """RNF-SEC-05/issue #25's "testado sem ligação à Internet" acceptance
    criterion: verification is pure local computation -- true by
    construction (this whole suite runs offline), asserted explicitly so a
    future change introducing an SMS/network-based factor would be caught.
    """
    user = User.objects.create_user(
        username="admin9", profile=Profile.INSTITUTION_ADMIN, password="pw12345"
    )
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)

    assert device.verify_token(_current_token(device)) is True
