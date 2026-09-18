"""Modelo Departamento (RF-CURR-01, docs/05-modelo-de-dados.md §5.4, issue #30)."""

from django.db import models

from apps.core.models import SyncedModel


class Department(SyncedModel):
    """ "Departamento" -- responsible for a set of courses' subjects.

    §5.4 also documents `responsavel_id` (FK to `hr.Funcionario`), left out
    here: `hr.Funcionario` isn't implemented yet (M3) -- see
    docs/implementation-decisions.md.
    """

    name = models.CharField("nome", max_length=150)

    class Meta(SyncedModel.Meta):
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
