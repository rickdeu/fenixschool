"""Modelo Disciplina (RF-CURR-03, docs/05-modelo-de-dados.md §5.6, issue #32)."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel

from .course_model import Course
from .curricular_year_model import CurricularYear


class Subject(SyncedModel):
    """ "Disciplina"."""

    class SubjectType(models.TextChoices):
        MANDATORY = "mandatory", "Obrigatória"
        OPTIONAL = "optional", "Opcional"
        EXTRACURRICULAR = "extracurricular", "Extracurricular"

    code = models.CharField("código", max_length=20)
    name = models.CharField("nome", max_length=150)
    abbreviation = models.CharField("abreviatura", max_length=20, blank=True, default="")
    created_on = models.DateField("data de criação")
    course = models.ForeignKey(
        Course, verbose_name="curso", on_delete=models.PROTECT, related_name="subjects"
    )
    curricular_year = models.ForeignKey(
        CurricularYear,
        verbose_name="ano curricular",
        on_delete=models.PROTECT,
        related_name="subjects",
    )
    term = models.ForeignKey(
        "core.AcademicTerm",
        verbose_name="período lectivo",
        on_delete=models.PROTECT,
        related_name="subjects",
        null=True,
        blank=True,
        help_text="Apenas quando a disciplina é semestral/trimestral, não anual.",
    )
    cycle = models.ForeignKey(
        "core.AcademicCycle",
        verbose_name="ciclo",
        on_delete=models.PROTECT,
        related_name="subjects",
    )
    subject_type = models.CharField(
        "tipo de disciplina", max_length=20, choices=SubjectType.choices
    )
    weekly_hours = models.PositiveSmallIntegerField("carga horária semanal")

    class Meta(SyncedModel.Meta):
        verbose_name = "disciplina"
        verbose_name_plural = "disciplinas"
        ordering = ["course", "curricular_year", "name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        errors = {}
        if self.curricular_year_id and self.course_id:
            if self.curricular_year.course_id != self.course_id:
                errors["curricular_year"] = "O ano curricular tem de pertencer ao mesmo curso."
        if self.term_id and self.institution_id and self.term.institution_id != self.institution_id:
            errors["term"] = "O período lectivo tem de pertencer à mesma instituição."
        if (
            self.cycle_id
            and self.institution_id
            and self.cycle.institution_id != self.institution_id
        ):
            errors["cycle"] = "O ciclo lectivo tem de pertencer à mesma instituição."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
