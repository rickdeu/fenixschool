"""A minimal Celery task used to prove the central node's worker actually
processes tasks -- see docs/11-implantacao-e-operacoes.md §11.2 (issue #8's
acceptance criterion). Only ever dispatched under
`config.settings.central_node`; the local node has no Celery worker to run it.
"""

from celery import shared_task


@shared_task
def ping() -> str:
    return "pong"
