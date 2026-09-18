"""Academic calendar: Ano Lectivo / Período Lectivo / Ciclo Lectivo / Dia Não
Lectivo (issue #16, docs/05-modelo-de-dados.md §5.3, RF-INST-03/04/05/07).

Per-institution business data (each school configures its own academic years,
terms, cycles and non-teaching days) -- unlike `core`'s national reference
tables (apps/core/models/reference.py), these are `SyncedModel` subclasses.
"""

from django.core.exceptions import ValidationError
from django.db import models

from .base import SyncedModel


class AcademicYear(SyncedModel):
    """ "Ano Lectivo" (RF-INST-03) -- e.g. "2026/2027"."""

    designation = models.CharField("designação", max_length=20)
    start_date = models.DateField("data de início")
    end_date = models.DateField("data de fim")
    is_current = models.BooleanField("é o ano lectivo corrente", default=False)

    class Meta(SyncedModel.Meta):
        verbose_name = "ano lectivo"
        verbose_name_plural = "anos lectivos"
        ordering = ["-start_date"]
        constraints = [
            # RF-INST-03 / issue #16's acceptance criterion: at most one
            # current academic year per institution -- a partial unique
            # index, not just application-level validation, since this must
            # hold even under concurrent writes.
            models.UniqueConstraint(
                fields=["institution"],
                condition=models.Q(is_current=True),
                name="core_academicyear_one_current_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.designation

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError(
                {"end_date": "A data de fim deve ser posterior à data de início."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AcademicTerm(SyncedModel):
    """ "Trimestre" (RF-INST-04, "Período Lectivo" no modelo de dados) -- a
    trimester/semester within an `AcademicYear`. Chamado de "Trimestre" em
    toda a interface, por pedido explícito do utilizador."""

    academic_year = models.ForeignKey(
        AcademicYear, verbose_name="ano lectivo", on_delete=models.CASCADE, related_name="terms"
    )
    number = models.PositiveSmallIntegerField("número")
    start_date = models.DateField("data de início")
    end_date = models.DateField("data de fim")

    class Meta(SyncedModel.Meta):
        verbose_name = "trimestre"
        verbose_name_plural = "trimestres"
        ordering = ["academic_year", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "number"],
                name="core_academicterm_unique_number_per_year",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}.º Trimestre — {self.academic_year}"

    def clean(self):
        errors = {}
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors["end_date"] = "A data de fim deve ser posterior à data de início."
        if self.academic_year_id and self.institution_id:
            if self.academic_year.institution_id != self.institution_id:
                errors["academic_year"] = "O ano lectivo tem de pertencer à mesma instituição."
            elif self.start_date and self.end_date:
                # A term must fall entirely within its own academic year --
                # issue #16's "período dentro do ano lectivo" acceptance
                # criterion.
                if (
                    self.start_date < self.academic_year.start_date
                    or self.end_date > self.academic_year.end_date
                ):
                    errors["__all__"] = "O trimestre tem de estar contido dentro do ano lectivo."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AcademicCycle(SyncedModel):
    """ "Ciclo Lectivo" (RF-INST-05) -- e.g. "1.º Ciclo", "2.º Ciclo".

    Its relationship to Cursos (RF-INST-05) is added as a FK on `Curso`
    itself once that model exists (`apps.academic`, issue #31) -- not
    fabricated here against a model that doesn't exist yet.
    """

    designation = models.CharField("designação", max_length=100)
    order = models.PositiveSmallIntegerField("ordem")

    class Meta(SyncedModel.Meta):
        verbose_name = "ciclo lectivo"
        verbose_name_plural = "ciclos lectivos"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "order"],
                name="core_academiccycle_unique_order_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return self.designation


class NonTeachingDay(SyncedModel):
    """ "Dia Não Lectivo" (RF-INST-07) -- a holiday or other non-teaching day.

    `scope` is descriptive only (how the day is displayed/filtered, per
    issue #20's "filtro por abrangência"), not a cross-tenant sharing
    mechanism: every institution keeps its own rows, including for national
    holidays, consistent with the project's tenant-isolation rules.
    """

    class Scope(models.TextChoices):
        NATIONAL = "nacional", "Nacional"
        PROVINCIAL = "provincial", "Provincial"
        INSTITUTIONAL = "institucional", "Institucional"

    date = models.DateField("data")
    description = models.CharField("descrição", max_length=255)
    scope = models.CharField("abrangência", max_length=20, choices=Scope.choices)

    class Meta(SyncedModel.Meta):
        verbose_name = "dia não lectivo"
        verbose_name_plural = "dias não lectivos"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.description} ({self.date:%d/%m/%Y})"
