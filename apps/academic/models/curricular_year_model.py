"""Modelo Ano Curricular (RF-CURR-04, docs/05-modelo-de-dados.md §5.7, issue #33)."""

from django.db import models

from apps.core.models import SyncedModel

from .course_model import Course


class CurricularYear(SyncedModel):
    """ "Ano Curricular" -- distinct from the administrative "classe" (10.ª,
    11.ª, ...), so a repeating student can be in the same "classe" across
    different academic years."""

    course = models.ForeignKey(
        Course, verbose_name="curso", on_delete=models.CASCADE, related_name="curricular_years"
    )
    number = models.PositiveSmallIntegerField("número")
    equivalent_grade = models.CharField(
        "classe equivalente", max_length=50, help_text='Ex.: "10.ª classe".'
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "ano curricular"
        verbose_name_plural = "anos curriculares"
        ordering = ["course", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "number"],
                name="academic_curricularyear_unique_number_per_course",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}.º Ano — {self.course} ({self.equivalent_grade})"
