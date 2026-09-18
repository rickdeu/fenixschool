"""The FenixSchool custom user model.

See docs/05-modelo-de-dados.md §5.24, docs/04-arquitetura-tecnica.md §4.4.1 and
docs/07-perfis-permissoes-e-fluxos.md §7.1 for the full profile matrix (issue #21).

`User` intentionally does *not* inherit `SyncedModel` (apps/core/models/base.py):
its `institution` foreign key must be nullable for the Super Administrator
profile, which has no fixed institution at all, whereas `SyncedModel.institution`
is always required.

Two things §5.24 mentions are deliberately not here yet, left to the issues that
actually need them instead of being fabricated ahead of time:
- Login by email/phone instead of username (§5.24's "email (login)") --
  issue #24 ("Login sem seleção de escola"), which needs its own authentication
  backend, not just a `USERNAME_FIELD` change.
- "ultimo_acesso" -- already covered by `AbstractBaseUser.last_login`
  (inherited via `AbstractUser`), so not duplicated as a separate field.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid6 import uuid7


class Profile(models.TextChoices):
    """The system's user profiles -- see docs/07-perfis-permissoes-e-fluxos.md §7.1."""

    SUPER_ADMIN = "super_admin", "Super Administrator"
    INSTITUTION_ADMIN = "institution_admin", "Institution Administrator"
    PEDAGOGICAL_DIRECTION = "pedagogical_direction", "Pedagogical Direction"
    SECRETARY = "secretary", "School Secretary"
    TEACHER = "teacher", "Teacher"
    HOMEROOM_TEACHER = "homeroom_teacher", "Homeroom Teacher"
    FINANCE = "finance", "Finance / Treasury"
    HR = "hr", "Human Resources"
    LIBRARY = "library", "Library"
    GUARDIAN = "guardian", "Guardian"
    STUDENT = "student", "Student"


class User(AbstractUser):
    """The FenixSchool user model -- see the module docstring for current scope."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    institution = models.ForeignKey(
        "core.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
        help_text=(
            "Required for every profile except Super Administrator, who has no "
            "fixed institution of their own. Set once at account creation and "
            "never edited through an ordinary form afterwards -- see "
            "docs/04-arquitetura-tecnica.md §4.4.1."
        ),
    )
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
        help_text="The user who registered this account -- see §4.4.1.",
    )
    profile = models.CharField(
        max_length=32,
        choices=Profile.choices,
        default=Profile.SUPER_ADMIN,
    )
    phone = models.CharField(max_length=20, blank=True, default="")
    preferred_language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="pt",
        help_text=(
            "A personal interface preference, never an institution/node-wide "
            "setting -- RNF-LOC-07: two users at the same school can each use "
            "a different interface language at the same time."
        ),
    )
    @property
    def is_super_admin(self) -> bool:
        return self.profile == Profile.SUPER_ADMIN

    @property
    def is_2fa_active(self) -> bool:
        """Whether TOTP two-factor authentication is set up for this
        account -- always computed from the real `TOTPDevice` state (issue
        #25), never a separately stored flag that could drift out of sync
        with it (e.g. if a device were deleted directly via the Django
        Admin). Mandatory for Institution Administrator, Super
        Administrator and Finance profiles -- see
        `apps.accounts.services.requires_two_factor`.
        """
        from django_otp.plugins.otp_totp.models import TOTPDevice

        return TOTPDevice.objects.filter(user=self, confirmed=True).exists()
