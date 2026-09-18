"""Seeds a full demonstration institution for local development -- see
`apps.core.demo_data` for what it creates and why. No-op unless
`settings.DEBUG` (never touches a real deployment), and idempotent (safe to
run on every `docker compose up`/`migrate`, not just the first time).
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.demo_data import DEMO_INSTITUTION_NAME, DEMO_PASSWORD, seed_demo_data


class Command(BaseCommand):
    help = (
        "Seeds a full demo institution (50+ students, users, notas, ...). No-op unless DEBUG=True."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write("DEBUG is off -- skipping demo data seeding.")
            return

        created = seed_demo_data()
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Seeded demo institution '{DEMO_INSTITUTION_NAME}' "
                    f"(every demo user's password: {DEMO_PASSWORD})."
                )
            )
        else:
            self.stdout.write(
                f"Demo institution '{DEMO_INSTITUTION_NAME}' already exists -- skipping."
            )
