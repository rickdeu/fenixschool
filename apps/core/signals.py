"""Signals da app `core` (ex.: disparo de changelog de sincronização e auditoria).

Also binds `request.institution_id` (set by `apps.core.middleware.TenantMiddleware`)
into every log line `django_structlog.middlewares.RequestMiddleware` emits for a
request, so a school's own logs can be filtered by institution -- see the
"Logging" section of config/settings/base.py (issue #13, RNF-OBS-01).
"""

import structlog
from django.dispatch import receiver
from django_structlog import signals as structlog_signals


@receiver(structlog_signals.bind_extra_request_metadata)
def bind_institution_id(request, logger, log_kwargs, **kwargs):
    # `getattr` rather than `request.institution_id`: defensive against the
    # (normally impossible) case of this firing for a request that never
    # reached `TenantMiddleware` -- e.g. an exception raised inside that
    # middleware itself, before it could set the attribute.
    institution_id = getattr(request, "institution_id", None)
    structlog.contextvars.bind_contextvars(
        # `institution_id` is a UUID (core.Institution.id), not natively JSON
        # serializable -- stringify it, but keep `None` as-is (a Super
        # Administrator viewing no particular institution) rather than the
        # literal string "None".
        institution_id=str(institution_id) if institution_id is not None else None
    )
