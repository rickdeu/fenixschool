"""A minimal Celery task used to prove the central node's worker actually
processes tasks -- see docs/11-implantacao-e-operacoes.md §11.2 (issue #8's
acceptance criterion). Only ever dispatched under
`config.settings.central_node`; the local node has no Celery worker to run it.

The import below is guarded the same way as config/__init__.py: `celery` is
only installed under requirements/central_node.txt, but this module is
imported directly by its own test (apps/core/tests/test_tasks.py), which
pytest collects regardless of environment -- so this must not raise
ImportError under the base/local-node/CI dependency set, where `celery` is
never installed at all.
"""

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - exercised by the base/local-node/CI dependency set

    def shared_task(func):
        return func


@shared_task
def ping() -> str:
    return "pong"
