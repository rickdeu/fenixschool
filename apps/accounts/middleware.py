"""Resolves the interface language from the user's own preference, never the
browser -- issue #149, docs/10-stack-tecnologica-e-estrutura-projeto.md §10.4.1,
RNF-LOC-06/07.
"""

from django.conf import settings
from django.utils import translation


class PreferredLanguageMiddleware:
    """Activates `request.user.preferred_language` for every request.

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
