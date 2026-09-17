"""Tests for the security headers configured in `config/settings/base.py` (issue #146,
docs/09-seguranca-e-privacidade.md §9.7)."""

import pytest
from django.conf import settings


@pytest.mark.django_db
def test_response_carries_the_expected_security_headers(client):
    response = client.get("/admin/login/")

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"

    csp = response["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "'unsafe-eval'" in csp  # Alpine.js expression evaluation
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_secure_ssl_settings_are_off_by_default_in_this_environment():
    # config.settings.test does not set DJANGO_SECURE_SSL, so the
    # HTTPS-only settings in base.py's conditional block never got applied --
    # asserting this here guards against them ever becoming unconditional
    # again, which would break every environment without TLS in front of it
    # (issue #142 is not done yet).
    assert getattr(settings, "SECURE_SSL_REDIRECT", False) is False
    assert getattr(settings, "SESSION_COOKIE_SECURE", False) is False
    assert getattr(settings, "CSRF_COOKIE_SECURE", False) is False


def test_secure_proxy_ssl_header_matches_nginx_forwarded_proto():
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
