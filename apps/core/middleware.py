"""`TenantMiddleware` -- resolves the current tenant institution for each request.

See docs/04-arquitetura-tecnica.md §4.4.4. Implements issue #5.
"""

from apps.core.context import reset_current_institution, set_current_institution
from apps.core.models import Institution


class TenantMiddleware:
    """Resolves `request.institution` from the authenticated user.

    A regular user's institution is fixed on their account and is never chosen
    manually (see docs/04-arquitetura-tecnica.md §4.4.1/§4.4.4):
    `request.institution` is simply set to `request.user.institution`.

    A Super Administrator has no institution of their own. Instead of an
    ambiguous default, they operate in an explicitly selected "viewing" context:
    the institution they are currently viewing is read from
    `request.session[SESSION_KEY]`, defaulting to `None` (no institution
    selected, i.e. a network-wide view) until they pick one.

    The resolved institution id is also pushed onto the tenant context consumed
    by `TenantManager` (see apps.core.context / apps.core.models.managers) for
    the duration of the request, and always reset afterwards so it never leaks
    into whatever runs next.
    """

    SESSION_KEY = "super_admin_selected_institution_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.institution = self._resolve_institution(request)
        request.institution_id = getattr(request.institution, "id", None)

        token = set_current_institution(request.institution_id)
        try:
            response = self.get_response(request)
        finally:
            reset_current_institution(token)
        return response

    def _resolve_institution(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        if user.is_super_admin:
            institution_id = request.session.get(self.SESSION_KEY)
            if not institution_id:
                return None
            return Institution.objects.filter(pk=institution_id).first()

        return user.institution
