"""The FenixSchool custom user model.

See docs/05-modelo-de-dados.md §5.24 and docs/07-perfis-permissoes-e-fluxos.md §7.1
for the full profile matrix. This model only implements what issues #3-#6 need:
institution-based tenancy and the Super Administrator flag `TenantMiddleware`
(apps/core/middleware.py) relies on. Additional fields (phone number, two-factor
flag, preferred language, etc. -- see §5.24) are left to a dedicated `accounts`
implementation issue.

`User` intentionally does *not* inherit `SyncedModel` (apps/core/models/base.py):
its `institution` foreign key must be nullable for the Super Administrator
profile, which has no fixed institution at all, whereas `SyncedModel.institution`
is always required.
"""

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

    @property
    def is_super_admin(self) -> bool:
        return self.profile == Profile.SUPER_ADMIN
