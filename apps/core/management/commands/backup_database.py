"""Manual trigger for `apps.core.services.backup_database` -- the same backup
the daily Django-Q2 schedule already runs automatically (issue #166)."""

from django.core.management.base import BaseCommand

from apps.core.services import backup_database


class Command(BaseCommand):
    help = "Runs a pg_dump backup of the database, gzipped to BACKUP_DIR."

    def handle(self, *args, **options):
        path = backup_database()
        self.stdout.write(self.style.SUCCESS(f"Cópia de segurança guardada em {path}"))
