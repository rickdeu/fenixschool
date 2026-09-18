"""Modelo Candidato (RF-MAT-10, docs/05-modelo-de-dados.md §5.14, issue #42)."""

from django.db import models

from apps.core.models import SyncedModel


class Candidate(SyncedModel):
    """ "Candidato" -- pre-application before the actual Inscrição, fed also by
    the public site's pre-application form (`apps.public_site`, issue #102)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ADMITTED = "admitted", "Admitido"
        REJECTED = "rejected", "Rejeitado"

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
        "estado", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    application_date = models.DateField("data de candidatura", auto_now_add=True)

    class Meta(SyncedModel.Meta):
        verbose_name = "candidato"
        verbose_name_plural = "candidatos"
        ordering = ["-application_date"]

    def __str__(self) -> str:
        return self.full_name

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
