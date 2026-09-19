"""Modelo Matrícula (RF-MAT-05, docs/05-modelo-de-dados.md §5.15, issue #43).

The yearly act that associates an already-inscribed Student
(`enrollment.Student`, issue #39) with a Course/AcademicYear/SchoolClass --
distinct from, and repeated every academic year unlike, the one-time
Inscrição. Never conflate the two.
"""

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.models import SyncedModel
from apps.core.models.managers import TenantManager, TenantQuerySet

# Only FKs pointing at other per-institution SyncedModel rows belong here --
# `presented_document_type` (core.IdentificationDocumentType) is shared
# national reference data with no `institution` of its own (see the bug this
# exact mistake caused on `enrollment.Student`, fixed before issue #39/#41
# merged).
_INSTITUTION_SCOPED_FIELDS = (
    ("student", "aluno"),
    ("course", "curso"),
    ("academic_year", "ano lectivo"),
    ("school_class", "turma"),
    ("cycle", "ciclo lectivo"),
    ("curricular_year", "ano curricular"),
    ("previous_enrollment", "matrícula anterior"),
)


class EnrollmentQuerySet(TenantQuerySet):
    def for_guardian(self, user):
        """§7.2 (Encarregado de Educação -- "só vê os seus educandos",
        issue #29): restricts to Matrículas of students actually linked, by
        a non-revoked `StudentGuardian`, to this user's own `Guardian`
        record."""
        return self.filter(
            student__guardian_links__guardian__user=user,
            student__guardian_links__is_deleted=False,
        )


class EnrollmentManager(TenantManager.from_queryset(EnrollmentQuerySet)):
    """`TenantManager`'s own tenant-scoping `get_queryset()`, plus
    `EnrollmentQuerySet`'s `for_guardian()`."""


class Enrollment(SyncedModel):
    """ "Matrícula".

    §5.15 also documents `funcionario_id` (FK to `hr.Funcionario`, "quem
    processou"), left out here: `hr.Funcionario` isn't implemented yet (M3)
    -- see docs/implementation-decisions.md.
    """

    objects = EnrollmentManager()

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Activa"
        CANCELLED = "cancelled", "Anulada"
        TRANSFERRED = "transferred", "Transferida"
        COMPLETED = "completed", "Concluída"

    # Assigned automatically on first save -- sequential per institution
    # *and* academic year (unlike Student.student_number, which is only
    # scoped by institution).
    enrollment_number = models.PositiveIntegerField(
        "número de matrícula",
        editable=False,
        help_text="Sequencial por instituição e ano lectivo.",
    )
    date = models.DateField("data", auto_now_add=True)
    student = models.ForeignKey(
        "enrollment.Student",
        verbose_name="aluno",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        "academic.Course",
        verbose_name="curso",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    academic_year = models.ForeignKey(
        "core.AcademicYear",
        verbose_name="ano lectivo",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    school_class = models.ForeignKey(
        "academic.SchoolClass",
        verbose_name="turma",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    cycle = models.ForeignKey(
        "core.AcademicCycle",
        verbose_name="ciclo lectivo",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    curricular_year = models.ForeignKey(
        "academic.CurricularYear",
        verbose_name="ano curricular",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField(
        "estado da matrícula", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    presented_document_type = models.ForeignKey(
        "core.IdentificationDocumentType",
        verbose_name="tipo de documento apresentado",
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    presented_document_number = models.CharField("número do documento apresentado", max_length=50)
    document_issue_date = models.DateField("data de emissão do documento")
    document_issue_place = models.CharField("local de emissão do documento", max_length=100)
    notes = models.TextField("observações", blank=True, default="")
    is_repeating = models.BooleanField("é repetente", default=False)
    previous_enrollment = models.ForeignKey(
        "self",
        verbose_name="matrícula anterior",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="next_enrollments",
        help_text="Referência à matrícula do ano anterior (histórico/retenção/transferência).",
    )
    cancellation_reason = models.TextField(
        "motivo da anulação",
        blank=True,
        default="",
        help_text="Issue #51/docs/06 §6.4: obrigatório ao anular (Estado = Anulada), vazio até lá.",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        ordering = ["-academic_year", "-enrollment_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "academic_year", "enrollment_number"],
                name="enrollment_enrollment_unique_number_per_institution_year",
            ),
        ]

    def __str__(self) -> str:
        return f"Matrícula #{self.enrollment_number} — {self.student} ({self.academic_year})"

    def clean(self):
        errors = {}
        for field_name, label in _INSTITUTION_SCOPED_FIELDS:
            related = getattr(self, field_name, None)
            if (
                related is not None
                and self.institution_id
                and related.institution_id != self.institution_id
            ):
                errors[field_name] = f"O(a) {label} tem de pertencer à mesma instituição."

        if self.status == self.Status.CANCELLED and not self.cancellation_reason.strip():
            errors["cancellation_reason"] = (
                "A anulação de uma matrícula exige um motivo (issue #51)."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding and not self.enrollment_number:
            with transaction.atomic():
                last_number = (
                    Enrollment.all_objects.select_for_update()
                    .filter(institution=self.institution, academic_year=self.academic_year)
                    .aggregate(models.Max("enrollment_number"))["enrollment_number__max"]
                    or 0
                )
                self.enrollment_number = last_number + 1
                self.full_clean()
                super().save(*args, **kwargs)
        else:
            self.full_clean()
            super().save(*args, **kwargs)
