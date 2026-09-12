"""A trivial test for the `ping` Celery task -- see apps/core/tasks.py."""

from apps.core.tasks import ping


def test_ping_returns_pong():
    # Calling a Celery task directly (rather than through `.delay()`/`.apply_async()`)
    # runs it synchronously in-process, with no broker involved -- exactly what we
    # want here, since this task only exists to prove a worker can run *something*.
    assert ping() == "pong"
