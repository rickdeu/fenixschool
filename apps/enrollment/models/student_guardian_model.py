"""Modelo EncarregadoAluno (tabela associativa) — RF-MAT-11, docs/05-modelo-de-
dados.md §5.13, issue #41."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel

from .guardian_model import Guardian
from .student_model import Student


class StudentGuardian(SyncedModel):
    """ "EncarregadoAluno" -- lets a Student have more than one Guardian (e.g.
    father and mother), with one marked as principal for communication/
    financial purposes."""

    student = models.ForeignKey(
        Student, verbose_name="aluno", on_delete=models.CASCADE, related_name="guardian_links"
    )
    guardian = models.ForeignKey(
        Guardian, verbose_name="encarregado", on_delete=models.CASCADE, related_name="student_links"
    )
    is_primary = models.BooleanField(
        "encarregado principal",
        default=False,
        help_text="Contacto principal (financeiro/comunicação).",
    )
    financially_responsible = models.BooleanField("responsável financeiro", default=False)

    class Meta(SyncedModel.Meta):
        verbose_name = "encarregado do aluno"
        verbose_name_plural = "encarregados do aluno"
        ordering = ["student", "-is_primary"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"],
                name="enrollment_studentguardian_unique_pair",
            ),
            # RF-MAT-11 / issue #41's acceptance criterion: at most one
            # principal guardian per student.
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(is_primary=True),
                name="enrollment_studentguardian_one_primary_per_student",
            ),
        ]

    def __str__(self) -> str:
        marker = " (principal)" if self.is_primary else ""
        return f"{self.guardian} — {self.student}{marker}"

    def clean(self):
        errors = {}
        for field_name, label in (("student", "aluno"), ("guardian", "encarregado")):
            related = getattr(self, field_name, None)
            if (
                related is not None
                and self.institution_id
                and related.institution_id != self.institution_id
            ):
                errors[field_name] = f"O {label} tem de pertencer à mesma instituição."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
