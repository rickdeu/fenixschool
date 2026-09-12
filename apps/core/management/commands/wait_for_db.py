"""A management command that blocks until the default database is reachable.

Used by scripts/entrypoint.sh as cheap defense-in-depth: both
docker-compose.local-node.yml and docker-compose.central-node.yml already
gate every service on `db: condition: service_healthy`, so this should
rarely have to wait in practice -- but that guarantee only holds when this
image runs *through* one of those compose files, not for an ad-hoc
`docker run`, or any other orchestration that doesn't attach a healthcheck to
Postgres. See docs/11-implantacao-e-operacoes.md §11.3.
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
