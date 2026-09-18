"""Modelo Aluno (RF-MAT-02, docs/05-modelo-de-dados.md §5.11, issue #39).

Corresponds to the **Inscrição** act (see docs/07-perfis-permissoes-e-fluxos.md
and the project glossary): a single, perpetual record per student, distinct
from the yearly **Matrícula** (`enrollment.Enrollment`, issue #43). Never
conflate the two -- a student is inscribed once, ever; enrolled again every
academic year.
"""

from django.db import models, transaction

from apps.core.models import SyncedModel


class Student(SyncedModel):
    """ "Aluno"."""

    class Gender(models.TextChoices):
        MALE = "male", "Masculino"
        FEMALE = "female", "Feminino"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        TRANSFERRED = "transferred", "Transferido"
        COMPLETED = "completed", "Concluído"
        INACTIVE = "inactive", "Inactivo"

    # Assigned automatically on first save (see `save()` below) -- never by
    # the caller, and never reassigned afterwards.
    student_number = models.PositiveIntegerField(
        "número de aluno", editable=False, help_text="Sequencial por instituição."
    )

    first_name = models.CharField("nome", max_length=100)
    last_name = models.CharField("sobrenome", max_length=100)
    birth_date = models.DateField("data de nascimento")
    gender = models.CharField("género", max_length=10, choices=Gender.choices)
    photo = models.ImageField("foto", upload_to="students/photos/", null=True, blank=True)

    # BI/Cédula Pessoal/Passaporte/Assento de Nascimento already exist as
    # core's national reference data (apps/core/models/reference.py) --
    # reused here via FK instead of a duplicate hardcoded choice.
    document_type = models.ForeignKey(
        "core.IdentificationDocumentType",
        verbose_name="tipo de documento",
        on_delete=models.PROTECT,
        related_name="students",
    )
    document_number = models.CharField("número do documento", max_length=50)
    document_issue_date = models.DateField("data de emissão do documento")
    document_issue_place = models.CharField(
        "local de emissão do documento", max_length=100, help_text='Ex.: "Nacional - Luanda".'
    )

    province = models.ForeignKey(
        "core.Province",
        verbose_name="província",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    municipality = models.ForeignKey(
        "core.Municipality",
        verbose_name="município",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )
    district_or_commune = models.CharField(
        "distrito/comuna", max_length=100, blank=True, default=""
    )
    neighborhood = models.CharField("bairro", max_length=100, blank=True, default="")
    street = models.CharField("rua", max_length=150, blank=True, default="")
    house_number = models.CharField("número da casa", max_length=20, blank=True, default="")

    # "Aplicável se maior/trabalhador-estudante" -- optional.
    profession = models.ForeignKey(
        "core.Profession",
        verbose_name="profissão",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="students",
    )

    mobile_phone = models.CharField("telemóvel", max_length=20, blank=True, default="")
    landline_phone = models.CharField("telefone fixo", max_length=20, blank=True, default="")
    email = models.EmailField("email", blank=True, default="")

    registration_date = models.DateField("data de inscrição", auto_now_add=True)
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "aluno"
        verbose_name_plural = "alunos"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student_number"],
                name="enrollment_student_unique_number_per_institution",
            ),
            # RF-MAT-03: anti-duplication by identification document.
            models.UniqueConstraint(
                fields=["institution", "document_type", "document_number"],
                name="enrollment_student_unique_document_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} (#{self.student_number})"

    def save(self, *args, **kwargs):
        # Note: `province`/`municipality` are national reference data
        # (apps/core/models/reference.py), shared by every institution --
        # unlike `document_type`/`profession`, they have no `institution` of
        # their own to validate against (same as `core.Institution`'s own
        # `province`/`municipality` fields).
        if self._state.adding and not self.student_number:
            with transaction.atomic():
                # `all_objects` (not the tenant-filtered `objects`): a
                # soft-deleted student's number must never be reused, and
                # `select_for_update()` serializes concurrent inscriptions at
                # the same institution against each other (RNF: sequential
                # numbers are a documented select_for_update() case).
                last_number = (
                    Student.all_objects.select_for_update()
                    .filter(institution=self.institution)
                    .aggregate(models.Max("student_number"))["student_number__max"]
                    or 0
                )
                self.student_number = last_number + 1
                self.full_clean()
                super().save(*args, **kwargs)
        else:
            self.full_clean()
            super().save(*args, **kwargs)
