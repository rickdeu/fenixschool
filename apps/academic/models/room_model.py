"""Modelo Sala (RF-CURR-07, docs/05-modelo-de-dados.md §5.9, issue #35)."""

from django.db import models

from apps.core.models import SyncedModel


class Room(SyncedModel):
    """ "Sala"."""

    designation = models.CharField("designação", max_length=100)
    capacity = models.PositiveSmallIntegerField("capacidade")

    class Meta(SyncedModel.Meta):
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ["designation"]

    def __str__(self) -> str:
        return self.designation
