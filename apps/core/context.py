"""The current tenant (institution) context — consulted by `TenantManager`.

The "current" value (per HTTP request, sync task, or test) is held in a
`contextvars.ContextVar`, which works correctly with both threads and async code
(unlike a plain global variable or `threading.local`).

In production this context is set at the start of each HTTP request by
`core.middleware.TenantMiddleware` (see docs/04-arquitetura-tecnica.md §4.4.4),
which resolves the institution from the authenticated user
(`request.user.institution`) and calls `set_current_institution(...)`, restoring
the previous value at the end of the request.

In tests and system tasks (e.g. the sync engine, maintenance commands), use the
`tenant_context(...)` context manager instead:

    from apps.core.context import tenant_context

    with tenant_context(institution.id):
        Student.objects.all()  # already filtered by `institution`
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_current_institution_id: ContextVar[Any] = ContextVar("current_institution_id", default=None)


def get_current_institution() -> Any:
    """Return the id of the current tenant institution, or `None` if none is active."""
    return _current_institution_id.get()


def set_current_institution(institution_id: Any) -> Token:
    """Set the current tenant institution.

    Returns a `Token` that must be passed to `reset_current_institution` to
    restore the previous value (`tenant_context` already takes care of this).
    """
    return _current_institution_id.set(institution_id)


def reset_current_institution(token: Token) -> None:
    """Restore the tenant context to what it was before the matching `set_current_institution`."""
    _current_institution_id.reset(token)


@contextmanager
def tenant_context(institution_id: Any):
    """Context manager that activates `institution_id` as the current tenant.

    Always restores the previous value on exit, even on an exception, so a
    tenant context never "leaks" into code that runs afterwards.
    """
    token = set_current_institution(institution_id)
    try:
        yield
    finally:
        reset_current_institution(token)
