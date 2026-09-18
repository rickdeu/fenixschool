"""Middlewares da app `accounts`."""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse
from django.utils import translation

from .services import (
    get_session_timeout_seconds,
    get_two_factor_redirect_url_name,
    requires_two_factor,
)


class PreferredLanguageMiddleware:
    """Resolves the interface language from the user's own preference, never
    the browser -- issue #149, docs/10-stack-tecnologica-e-estrutura-projeto.md
    §10.4.1, RNF-LOC-06/07.

    Activates `request.user.preferred_language` for every request.

    Runs after `AuthenticationMiddleware` (needs `request.user`) and
    replaces `django.middleware.locale.LocaleMiddleware` entirely -- that
    middleware's Accept-Language/session-based detection is exactly what
    RNF-LOC-06/07 says the interface language must *not* come from. An
    anonymous request (no authenticated user yet, e.g. the login page
    itself) falls back to `settings.LANGUAGE_CODE` ("pt"), per issue #149's
    "Utilizador anónimo usa `pt` por omissão".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        language = (
            user.preferred_language
            if user is not None and user.is_authenticated
            else settings.LANGUAGE_CODE
        )
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            return self.get_response(request)
        finally:
            translation.deactivate()


class SessionIdleTimeoutMiddleware:
    """Expires a session after a period of inactivity, configurable by
    profile (issue #27, docs/09-seguranca-e-privacidade.md §9.2) -- shorter
    for higher-risk/shared-workstation profiles (see
    `settings.SESSION_TIMEOUT_MINUTES_BY_PROFILE`).

    Sets `request.session`'s expiry to that many seconds *from now* on
    every authenticated request, together with `SESSION_SAVE_EVERY_REQUEST
    = True` -- so it's a genuine sliding/inactivity window, not a fixed
    time-since-login one: each request pushes the expiry further out,
    and only a period of complete silence lets the session actually expire.
    Must run after `AuthenticationMiddleware`, which sets `request.user`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            request.session.set_expiry(get_session_timeout_seconds(user))
        return self.get_response(request)


class RequireTwoFactorMiddleware:
    """Blocks every page for the 3 profiles RNF-SEC-05 requires 2FA for
    (Administrador da Instituição/Super Administrador/Financeiro-Tesouraria)
    until they've confirmed a TOTP device and verified it for the current
    session -- issue #25.

    Relies on `request.user.is_verified()`, set by
    `django_otp.middleware.OTPMiddleware`, which must run before this one.
    The 2FA setup/verify views (and login/logout, to get there and to leave)
    are exempt -- otherwise a user who still needs to complete 2FA could
    never reach the page that lets them do so.
    """

    EXEMPT_VIEW_NAMES = {
        "accounts:login",
        "accounts:logout",
        "accounts:two_factor_setup",
        "accounts:two_factor_verify",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and requires_two_factor(user)
            and not user.is_verified()
            and self._current_view_name(request) not in self.EXEMPT_VIEW_NAMES
        ):
            return redirect(reverse(get_two_factor_redirect_url_name(user)))
        return self.get_response(request)

    @staticmethod
    def _current_view_name(request):
        try:
            return resolve(request.path_info).view_name
        except Resolver404:
            return None
