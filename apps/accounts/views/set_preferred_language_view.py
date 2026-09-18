"""View do selector de idioma pessoal (issue #28, RF-I18N-02, RNF-LOC-07)."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


@login_required
@require_POST
def set_preferred_language_view(request):
    """Updates the current user's own `preferred_language` -- never an
    institution-wide setting (RNF-LOC-07): each user changes only their own
    account, independent of every other user at the same institution.
    """
    language = request.POST.get("language")
    valid_codes = {code for code, _label in settings.LANGUAGES}
    if language in valid_codes:
        request.user.preferred_language = language
        request.user.save(update_fields=["preferred_language"])

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("accounts:landing_placeholder")
