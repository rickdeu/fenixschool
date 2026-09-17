"""Creates/updates a fixed local development superuser -- convenience for
running the project locally (see scripts/entrypoint.sh, docker-compose.local
-node.yml's `init` service).

Guarded by `settings.DEBUG` so this can never create a hardcoded-credential
account on a real deployment: `config/settings/local_node.py` and
`central_node.py` both default `DEBUG` to `False` regardless of what a stray
`.env` sets, so this is a safe no-op even if it were ever invoked outside a
genuine local dev environment.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import Profile, User

DEV_SUPERUSER_USERNAME = "root"
DEV_SUPERUSER_PASSWORD = "root"


class Command(BaseCommand):
    help = "Creates/updates a fixed local dev superuser (root/root). No-op unless DEBUG=True."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write("DEBUG is off -- skipping dev superuser creation.")
            return

        user, created = User.objects.get_or_create(
            username=DEV_SUPERUSER_USERNAME,
            defaults={"profile": Profile.SUPER_ADMIN, "is_staff": True, "is_superuser": True},
        )
        if not created:
            user.profile = Profile.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
        user.set_password(DEV_SUPERUSER_PASSWORD)
        user.save()

        verb = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} dev superuser '{DEV_SUPERUSER_USERNAME}' "
                f"(password: {DEV_SUPERUSER_PASSWORD})."
            )
        )
