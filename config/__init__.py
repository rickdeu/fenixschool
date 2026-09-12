"""Importing the Celery app here ensures it is loaded when Django starts, so
`@shared_task` decorated functions always use this app -- see config/celery.py
and https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html.

The import is wrapped in a try/except on purpose: `celery` is only installed
under the central node's requirements (requirements/central_node.txt) -- the
local node deliberately has no Celery/Redis at all (Django-Q2 instead, see
config/settings/local_node.py), and neither does the base dev/test
environment. Every settings module (config.settings.base included) executes
this file as Python imports its parent package, so this must not raise just
because `celery` happens not to be installed.
"""

try:
    from .celery import app as celery_app
except ImportError:
    celery_app = None

__all__ = ("celery_app",)
