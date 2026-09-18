"""Modelo Média/Nota Final (RF-AVAL-02, issue #58).

Not documented as its own entity in docs/05-modelo-de-dados.md (only "Nota",
§5.17, is) -- but RF-AVAL-02's own acceptance criterion, "ajuste manual
exige justificação registada em auditoria", needs a durable row to adjust
and to audit: a pure calculation with no persistence would have neither.
Kept deliberately minimal -- no "situação final"/aprovação fields, that is
issue #62's own scope -- just the calculated average, its optional manual
override, and the override's justification.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SyncedModel

from .grading_scale_model import GradingScale


class FinalGrade(SyncedModel):
    """ "Média"/"Nota Final" de uma disciplina, numa matrícula, num período
    lectivo -- o resultado de `apps.grading.services.calcular_media_disciplina`
    (fórmula parametrizada, RF-INST-06), com um eventual ajuste manual
    justificado (RF-AVAL-02) por cima.

    `calculated_value` só é escrito por
    `apps.grading.services.registar_media_final` (nunca directamente por um
    formulário) -- recalculável a qualquer momento (ex.: issue #61's
    avaliação de recurso) sem perder um ajuste manual já registado:
    `manual_override_value`/`override_reason` ficam intocados por um
    recálculo automático. `final_value` é o que efectivamente conta: o
    ajuste manual quando existe, senão o valor calculado.
    """

    enrollment = models.ForeignKey(
        "enrollment.Enrollment",
        verbose_name="matrícula",
        on_delete=models.PROTECT,
        related_name="final_grades",
    )
    subject = models.ForeignKey(
        "academic.Subject",
        verbose_name="disciplina",
        on_delete=models.PROTECT,
        related_name="final_grades",
    )
    academic_term = models.ForeignKey(
        "core.AcademicTerm",
        verbose_name="trimestre",
        on_delete=models.PROTECT,
        related_name="final_grades",
    )
    calculated_value = models.DecimalField(
        "média calculada",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))],
    )
    manual_override_value = models.DecimalField(
        "valor ajustado manualmente",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))],
    )
    override_reason = models.TextField("justificação do ajuste", blank=True, default="")
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ajustado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="final_grade_overrides",
    )
    overridden_at = models.DateTimeField("ajustado em", null=True, blank=True)

    class Meta(SyncedModel.Meta):
        verbose_name = "média final"
        verbose_name_plural = "médias finais"
        # Terminal (non-relation) fields only -- see `grading.Grade.Meta`'s
        # own comment: ordering by a bare `enrollment`/`subject` FK makes
        # Django recursively expand into that related model's own
        # `Meta.ordering`, chaining through Course/CurricularYear/
        # Department/Cycle and joining `core_institution` dozens of times
        # over for a single changelist query.
        ordering = [
            "-academic_term__start_date",
            "enrollment__student__first_name",
            "enrollment__student__last_name",
            "subject__name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "subject", "academic_term"],
                name="grading_finalgrade_unique_per_enrollment_subject_term",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.enrollment.student} - {self.subject} ({self.academic_term}): {self.final_value}"
        )

    @property
    def final_value(self) -> Decimal:
        """The value that actually counts: the manual override when one
        exists, otherwise the calculated average."""
        return (
            self.manual_override_value
            if self.manual_override_value is not None
            else self.calculated_value
        )

    @property
    def qualitative_level(self) -> GradingScale | None:
        return GradingScale.for_value(self.final_value)

    def clean(self):
        errors = {}

        for field_name, label in (
            ("enrollment", "matrícula"),
            ("subject", "disciplina"),
            ("academic_term", "trimestre"),
            ("overridden_by", "utilizador que ajustou"),
        ):
            related = getattr(self, field_name, None)
            institution_id = getattr(related, "institution_id", None)
            if (
                related is not None
                and self.institution_id
                and institution_id not in (None, self.institution_id)
            ):
                errors[field_name] = f"O(a) {label} tem de pertencer à mesma instituição."

        if (
            self.subject_id
            and self.enrollment_id
            and self.subject.curricular_year_id != self.enrollment.curricular_year_id
        ):
            errors["subject"] = "A disciplina tem de pertencer ao ano curricular da matrícula."

        if self.manual_override_value is not None and not self.override_reason.strip():
            errors["override_reason"] = (
                "O ajuste manual da média exige uma justificação (RF-AVAL-02)."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
