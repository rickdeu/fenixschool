"""Middleware da app `audit`."""

from .context import reset_current_actor, set_current_actor


class AuditActorMiddleware:
    """Makes the current request's user and IP available to
    `apps.audit.signals`'s model signal handlers (issue #140, RNF-AUD-01) --
    those never receive the `HttpRequest` themselves. Must run after
    `AuthenticationMiddleware`, which sets `request.user`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        actor = user if user is not None and user.is_authenticated else None
        tokens = set_current_actor(actor, request.META.get("REMOTE_ADDR"))
        try:
            return self.get_response(request)
        finally:
            reset_current_actor(tokens)
