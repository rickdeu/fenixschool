"""The `core.Institution` model — the root tenant of the whole system.

This is deliberately a minimal version: just enough to be a valid target for the
`SyncedModel.institution` foreign key at this stage of the technical foundation
(M0). The full data model (`tax_id`, `ministry_of_education_code`,
`province`/`municipality`, `logo`, `default_grading_formula`, etc. — see
docs/05-modelo-de-dados.md §5.2) is left to a dedicated `core` issue, so as not to
fabricate business fields that were not specified there.
"""

from django.db import models
from uuid6 import uuid7


class Institution(models.Model):
    """A school (the root tenant of the system).

    Does not inherit `SyncedModel`: it *is* the tenant, not a record owned by one,
    so it has no `institution` foreign key of its own.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "institution"
        verbose_name_plural = "institutions"

    def __str__(self) -> str:
        return self.name
