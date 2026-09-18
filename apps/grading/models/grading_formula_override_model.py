"""Sobreposição da fórmula de média por Curso/Disciplina (RF-INST-06,
docs/05-modelo-de-dados.md §5.2/§5.16, issue #18).

`core.Institution.default_grading_formula` holds the institution-wide default.
A row here overrides it for exactly one `academic.Course` *or* one
`academic.Subject` (never both, never neither -- see `clean()`) -- the more
specific Subject override wins over a Course override, which wins over the
institution default (`apps.grading.services.resolve_grading_formula`).
"""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel


class GradingFormulaOverride(SyncedModel):
    """ "Sobreposição da Fórmula de Média"."""

    course = models.ForeignKey(
        "academic.Course",
        verbose_name="curso",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grading_formula_overrides",
    )
    subject = models.ForeignKey(
        "academic.Subject",
        verbose_name="disciplina",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grading_formula_overrides",
    )
    weights = models.JSONField(
        "pesos",
        help_text="Mapa {designação do tipo de avaliação: peso}, com soma 1 (100%).",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "sobreposição da fórmula de média"
        verbose_name_plural = "sobreposições da fórmula de média"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "course"],
                condition=models.Q(course__isnull=False),
                name="grading_formulaoverride_one_per_course",
            ),
            models.UniqueConstraint(
                fields=["institution", "subject"],
                condition=models.Q(subject__isnull=False),
                name="grading_formulaoverride_one_per_subject",
            ),
        ]

    def __str__(self) -> str:
        target = self.subject or self.course
        return f"Fórmula de média de {target}"

    def clean(self):
        if bool(self.course_id) == bool(self.subject_id):
            raise ValidationError(
                "A sobreposição tem de indicar exactamente um Curso ou uma Disciplina, nunca "
                "os dois nem nenhum."
            )
        if (
            self.course_id
            and self.institution_id
            and self.course.institution_id != self.institution_id
        ):
            raise ValidationError({"course": "O curso tem de pertencer à mesma instituição."})
        if (
            self.subject_id
            and self.institution_id
            and self.subject.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"subject": "A disciplina tem de pertencer à mesma instituição."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
