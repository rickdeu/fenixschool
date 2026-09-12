"""A management command that blocks until the default database is reachable.

Used by docker/entrypoint.sh so gunicorn/Django-Q/Celery containers don't crash
on startup just because Postgres takes a few extra seconds to accept
connections (a common race in `docker compose up`, since dependency ordering
via `depends_on` only waits for the container to start, not for Postgres
itself to be ready -- see docs/11-implantacao-e-operacoes.md §11.3).
"""

import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait until the default database connection is available."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Maximum number of seconds to wait before giving up (default: 30).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="Seconds to sleep between connection attempts (default: 1).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        interval = options["interval"]
        deadline = time.monotonic() + timeout

        connection = connections["default"]
        while True:
            try:
                connection.ensure_connection()
            except OperationalError:
                if time.monotonic() >= deadline:
                    self.stderr.write(
                        self.style.ERROR(f"Database still unavailable after {timeout}s.")
                    )
                    raise
                self.stdout.write("Database unavailable, waiting...")
                time.sleep(interval)
            else:
                self.stdout.write(self.style.SUCCESS("Database is available."))
                return
