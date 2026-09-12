"""The Celery application used by the central node's worker/beat processes.

Only relevant when running under `config.settings.central_node`: the local
node uses Django-Q2 instead (see docs/10-stack-tecnologica-e-estrutura-projeto.md
§10.1 and config/settings/local_node.py) and never imports this module.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.central_node")

app = Celery("fenixschool")

# Read CELERY_* settings from Django's settings module (see
# config/settings/central_node.py) instead of hardcoding broker/backend here.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover a `tasks` module in every installed app (see apps/core/tasks.py
# for the one test task that exists at this stage of the technical
# foundation).
app.autodiscover_tasks()
