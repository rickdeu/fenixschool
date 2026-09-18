"""Modelo Situação Final (RF-AVAL-07, issue #62).

Not documented as its own entity in docs/05-modelo-de-dados.md (it only goes
as far as "Nota", §5.17) -- but RF-AVAL-06's "estado 'em recurso' suportado
até resolução" (issue #61) and RF-AVAL-07's own "resultado usado em
relatórios e no portal do aluno/encarregado" both need a durable, per-year
row to hold that state and to be queried from, not just an ephemeral
calculation recomputed on every page view.
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel


class FinalSituation(SyncedModel):
    """ "Situação Final" -- one row per `Enrollment` (a matrícula is already
    scoped to a single academic year), summarising whether the aluno passed
    every disciplina of their ano curricular, is still recovering some
    ("com disciplinas em atraso", RF-AVAL-06's avaliação de recurso), or
    failed the year outright.

    `institution.max_recoverable_subjects` -- itself not an officially
    confirmed normative value (see its own field docstring) -- is what
    separates `PENDING_RECOVERY` from `FAILED` in
    `apps.grading.services.calcular_situacao_final`, which is the only
    place that ever writes to this model; never edited by hand.
    """

    class Status(models.TextChoices):
        APPROVED = "approved", "Aprovado"
        PENDING_RECOVERY = "pending_recovery", "Com disciplinas em atraso"
        FAILED = "failed", "Reprovado"

    enrollment = models.OneToOneField(
        "enrollment.Enrollment",
        verbose_name="matrícula",
        on_delete=models.PROTECT,
        related_name="final_situation",
    )
    status = models.CharField("situação", max_length=20, choices=Status.choices)
    failed_subjects = models.ManyToManyField(
        "academic.Subject",
        verbose_name="disciplinas em atraso",
        related_name="final_situations_failed_in",
        blank=True,
    )
    calculated_at = models.DateTimeField("calculada em", auto_now=True)

    class Meta(SyncedModel.Meta):
        verbose_name = "situação final"
        verbose_name_plural = "situações finais"
        ordering = ["-calculated_at"]

    def __str__(self) -> str:
        return f"{self.enrollment.student} — {self.get_status_display()}"

    def clean(self):
        if (
            self.enrollment_id
            and self.institution_id
            and self.enrollment.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"enrollment": "A matrícula tem de pertencer à mesma instituição."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
