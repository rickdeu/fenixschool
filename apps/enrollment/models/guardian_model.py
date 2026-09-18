"""Modelo Encarregado de Educação (docs/05-modelo-de-dados.md §5.12, issue #40)."""

from django.conf import settings
from django.db import models

from apps.core.models import SyncedModel


class Guardian(SyncedModel):
    """ "Encarregado de Educação" -- legally/financially responsible for a
    Student, with optional portal access."""

    class Kinship(models.TextChoices):
        FATHER = "father", "Pai"
        MOTHER = "mother", "Mãe"
        TUTOR = "tutor", "Tutor"
        OTHER = "other", "Outro"

    full_name = models.CharField("nome completo", max_length=200)
    kinship = models.CharField("grau de parentesco", max_length=10, choices=Kinship.choices)

    # Same national reference table Student.document_type uses.
    document_type = models.ForeignKey(
        "core.IdentificationDocumentType",
        verbose_name="tipo de documento",
        on_delete=models.PROTECT,
        related_name="guardians",
    )
    document_number = models.CharField("número do documento", max_length=50)

    mobile_phone = models.CharField("telemóvel", max_length=20, blank=True, default="")
    landline_phone = models.CharField("telefone fixo", max_length=20, blank=True, default="")
    email = models.EmailField("email", blank=True, default="")
    # Plain text per §5.12 (unlike Student.profession, which reuses
    # core.Profession) -- the source table lists it as free text here.
    profession = models.CharField("profissão", max_length=100, blank=True, default="")

    province = models.ForeignKey(
        "core.Province",
        verbose_name="província",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guardians",
    )
    municipality = models.ForeignKey(
        "core.Municipality",
        verbose_name="município",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guardians",
    )
    district_or_commune = models.CharField(
        "distrito/comuna", max_length=100, blank=True, default=""
    )
    neighborhood = models.CharField("bairro", max_length=100, blank=True, default="")
    street = models.CharField("rua", max_length=150, blank=True, default="")
    house_number = models.CharField("número da casa", max_length=20, blank=True, default="")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="utilizador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardian_profile",
        help_text="Conta de acesso ao portal do Encarregado de Educação (opcional).",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "encarregado de educação"
        verbose_name_plural = "encarregados de educação"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name
