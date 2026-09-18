"""The current "actor" (user + IP) for audit-log entries -- consulted by
`apps.audit.signals`'s `post_save`/`post_delete` handlers.

Model signals never receive the `HttpRequest`, so there is no ordinary way
for them to know who performed the change or from where. Mirrors
`apps.core.context`'s tenant-institution `contextvars` pattern exactly, for
the same reason: it works correctly with both threads and async code
(unlike a plain global variable or `threading.local`), and is set once per
HTTP request by `apps.audit.middleware.AuditActorMiddleware`, restoring the
previous value at the end of the request.
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_current_user: ContextVar[Any] = ContextVar("audit_current_user", default=None)
_current_ip_address: ContextVar[Any] = ContextVar("audit_current_ip_address", default=None)


def get_current_user() -> Any:
    return _current_user.get()


def get_current_ip_address() -> Any:
    return _current_ip_address.get()


def set_current_actor(user: Any, ip_address: Any) -> tuple[Token, Token]:
    """Returns the tokens `reset_current_actor` needs to restore the
    previous values."""
    return _current_user.set(user), _current_ip_address.set(ip_address)


def reset_current_actor(tokens: tuple[Token, Token]) -> None:
    user_token, ip_token = tokens
    _current_user.reset(user_token)
    _current_ip_address.reset(ip_token)


@contextmanager
def audit_actor_context(user: Any, ip_address: Any = None):
    """Context manager version of `set_current_actor`/`reset_current_actor`
    -- for tests and system tasks (management commands, the sync engine)
    that create/modify audited rows outside of an ordinary HTTP request.
    """
    tokens = set_current_actor(user, ip_address)
    try:
        yield
    finally:
        reset_current_actor(tokens)
