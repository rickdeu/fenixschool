"""Modelo Candidato (RF-MAT-10, docs/05-modelo-de-dados.md §5.14, issue #42)."""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import SyncedModel


class Candidate(SyncedModel):
    """ "Candidato" -- pre-application before the actual Inscrição, fed also by
    the public site's pre-application form (`apps.public_site`, issue #102).

    A prova de aptidão is only administered "quando necessário" (feedback
    do utilizador) -- e.g. quando há mais candidatos do que vagas -- por
    isso `exam_score` fica opcional: `None` significa "nenhuma prova
    exigida para este candidato", não "reprovado".
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACCEPTED = "accepted", "Aceite (aguarda Inscrição)"
        ADMITTED = "admitted", "Admitido"
        REJECTED = "rejected", "Rejeitado"
        SECOND_CALL = "second_call", "Segunda Chamada"

    full_name = models.CharField("nome completo", max_length=200)
    birth_date = models.DateField("data de nascimento")
    # Same national reference table Student.document_type/Guardian.document_type
    # use. Only the number and expiry date are asked here -- no upload, and no
    # issue date/place, both left to the actual Inscrição form (issue #45),
    # which still has to collect everything else this pre-application never
    # captures (address, guardian, ...).
    document_type = models.ForeignKey(
        "core.IdentificationDocumentType",
        verbose_name="tipo de documento",
        on_delete=models.PROTECT,
        related_name="candidates",
    )
    document_number = models.CharField("número do documento", max_length=50)
    document_expiry_date = models.DateField("data de validade do documento")
    desired_course = models.ForeignKey(
        "academic.Course",
        verbose_name="curso pretendido",
        on_delete=models.PROTECT,
        related_name="candidates",
    )
    contact = models.CharField("contacto", max_length=100)
    status = models.CharField(
        "estado", max_length=15, choices=Status.choices, default=Status.PENDING
    )
    application_date = models.DateField("data de candidatura", auto_now_add=True)
    exam_score = models.DecimalField(
        "nota da prova de aptidão",
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("20"))],
        help_text=(
            "Escala 0-20 (a mesma da avaliação escolar) -- preenchida depois da "
            "prova de aptidão, só quando esta é exigida. Em branco: nenhuma prova "
            "foi exigida a este candidato."
        ),
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "candidato"
        verbose_name_plural = "candidatos"
        ordering = ["-application_date"]

    def __str__(self) -> str:
        return self.full_name

    @property
    def is_eligible_for_admission(self) -> bool:
        """Só um candidato "apto" pode ser admitido à Inscrição -- mas
        "apto" só é avaliado quando existe uma nota (`exam_score`); sem
        prova exigida, o candidato segue elegível como sempre foi."""
        if self.exam_score is None:
            return True
        return self.exam_score >= self.institution.admission_exam_passing_score

    def student_defaults(self) -> dict:
        """Field values a Student-creation form can pre-fill when admitting
        this candidate (issue #42's "Admitir" action) -- the Inscrição form
        (issue #45) still has to collect what a Candidate never captured
        (document issue date/place, address, guardian, ...), so this only
        ever seeds a form, never creates a Student by itself.

        `document_expiry_date` has no equivalent on `Student` (which tracks
        issue date/place instead, not expiry), so it isn't carried over.
        """
        first_name, _, last_name = self.full_name.partition(" ")
        return {
            "first_name": first_name,
            "last_name": last_name,
            "birth_date": self.birth_date,
            "document_type": self.document_type_id,
            "document_number": self.document_number,
        }
