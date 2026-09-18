"""Modelo Turma (RF-CURR-05, docs/05-modelo-de-dados.md §5.8, issue #34)."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel

from .course_model import Course
from .curricular_year_model import CurricularYear


class SchoolClass(SyncedModel):
    """ "Turma".

    `academic_term` is left nullable: the source table (§5.8) lists it
    without the "novo" marker the other added fields carry, but a class of
    students ordinarily stays together for the whole academic year, not just
    one term -- see docs/implementation-decisions.md.

    §5.8 also documents `director_turma_id` (FK to `hr.Funcionario`), left
    out here: `hr.Funcionario` isn't implemented yet (M3).
    """

    class Shift(models.TextChoices):
        MORNING = "morning", "Manhã"
        AFTERNOON = "afternoon", "Tarde"
        EVENING = "evening", "Noite"

    code = models.CharField("código", max_length=20)
    designation = models.CharField("designação", max_length=100)
    academic_year = models.ForeignKey(
        "core.AcademicYear",
        verbose_name="ano lectivo",
        on_delete=models.PROTECT,
        related_name="school_classes",
    )
    academic_term = models.ForeignKey(
        "core.AcademicTerm",
        verbose_name="trimestre",
        on_delete=models.PROTECT,
        related_name="school_classes",
        null=True,
        blank=True,
    )
    course = models.ForeignKey(
        Course, verbose_name="curso", on_delete=models.PROTECT, related_name="school_classes"
    )
    curricular_year = models.ForeignKey(
        CurricularYear,
        verbose_name="ano curricular",
        on_delete=models.PROTECT,
        related_name="school_classes",
    )
    # Decreto Presidencial 162/23: 36 alunos por omissão, até 45 nalgumas
    # regiões, 26 em turmas inclusivas -- valor configurável, não uma
    # constraint rígida (ver docs/legislacao/README.md).
    max_enrollment = models.PositiveSmallIntegerField("número máximo de inscritos", default=36)
    shift = models.CharField("turno", max_length=10, choices=Shift.choices)

    class Meta(SyncedModel.Meta):
        verbose_name = "turma"
        verbose_name_plural = "turmas"
        ordering = ["-academic_year", "designation"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "code"], name="academic_schoolclass_unique_code_per_year"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.designation} ({self.academic_year})"

    def active_enrollment_count(self) -> int:
        """Enrollments that currently occupy a vacancy in this class (issue
        #46, RF-MAT-07). Imports `Enrollment` locally, not at module level:
        `enrollment.Enrollment` refers back to `academic.SchoolClass` (via a
        lazy string FK), so importing it while this module is still being
        defined would be load-order-fragile -- safe once this method
        actually runs, since every app is fully loaded by then.
        """
        from apps.enrollment.models import Enrollment

        return self.enrollments.filter(
            status__in=[Enrollment.Status.PENDING, Enrollment.Status.ACTIVE]
        ).count()

    def clean(self):
        errors = {}
        for field_name, label in (
            ("academic_year", "ano lectivo"),
            ("academic_term", "trimestre"),
            ("course", "curso"),
            ("curricular_year", "ano curricular"),
        ):
            related = getattr(self, field_name, None)
            if (
                related is not None
                and self.institution_id
                and related.institution_id != self.institution_id
            ):
                errors[field_name] = f"O(a) {label} tem de pertencer à mesma instituição."
        if self.curricular_year_id and self.course_id:
            if self.curricular_year.course_id != self.course_id:
                errors["curricular_year"] = "O ano curricular tem de pertencer ao mesmo curso."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
