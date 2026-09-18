"""Modelo Tipo de Avaliação (RF-INST-06, docs/05-modelo-de-dados.md §5.16, issue #18).

Parametriza os componentes usados na fórmula de média (ex.: "MAC", "Prova
Trimestral", "Exame") -- `default_weight` é o peso proposto quando um
Curso/Disciplina ainda não tem uma sobreposição própria (ver
`apps.grading.services.resolve_grading_formula`).
"""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SyncedModel


class EvaluationType(SyncedModel):
    """ "Tipo de Avaliação"."""

    name = models.CharField("designação", max_length=50)
    default_weight = models.DecimalField(
        "peso por omissão",
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1"))],
        help_text="Peso por omissão na fórmula de média (0 a 1), sugerido ao configurar.",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "tipo de avaliação"
        verbose_name_plural = "tipos de avaliação"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                name="grading_evaluationtype_unique_name_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
