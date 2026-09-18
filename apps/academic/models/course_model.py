"""Modelo Curso (RF-CURR-02, docs/05-modelo-de-dados.md §5.5, issue #31)."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel

from .department_model import Department


class Course(SyncedModel):
    """ "Curso"."""

    code = models.CharField("código", max_length=20)
    name = models.CharField("nome", max_length=150)
    abbreviation = models.CharField("abreviatura", max_length=20, blank=True, default="")
    created_on = models.DateField("data de criação")
    department = models.ForeignKey(
        Department, verbose_name="departamento", on_delete=models.PROTECT, related_name="courses"
    )
    ministry_of_education_code = models.CharField(
        "código MED", max_length=50, blank=True, default=""
    )
    cycle = models.ForeignKey(
        "core.AcademicCycle",
        verbose_name="ciclo",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    duration_years = models.PositiveSmallIntegerField(
        "duração (anos)", help_text="Ex.: 4 anos (10.ª a 13.ª classe)."
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "curso"
        verbose_name_plural = "cursos"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="academic_course_unique_code_per_institution"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        if (
            self.cycle_id
            and self.institution_id
            and self.cycle.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"cycle": "O ciclo lectivo tem de pertencer à mesma instituição."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
