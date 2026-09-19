"""Modelo Presença/Falta (RF-FREQ-01, docs/05-modelo-de-dados.md §5.18,
issue #65).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel


def justification_attachment_upload_to(instance, filename):
    return f"attendance/justifications/{instance.institution_id}/{filename}"


class Attendance(SyncedModel):
    """ "Presença/Falta" -- um registo de presença de um aluno, numa aula
    concreta (`academic.Schedule`), num dia específico.

    `registered_by` é um `accounts.User` simples (perfil Docente/Diretor de
    Turma), não `hr.Funcionario` (§5.18 especifica-o assim, mas essa app
    ainda não existe -- M3) -- mesmo raciocínio já usado em
    `academic.Schedule.teacher`/`grading.Grade.teacher`.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Presente"
        ABSENT = "absent", "Falta"
        JUSTIFIED_ABSENT = "justified_absent", "Falta Justificada"

    student = models.ForeignKey(
        "enrollment.Student",
        verbose_name="aluno",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    enrollment = models.ForeignKey(
        "enrollment.Enrollment",
        verbose_name="matrícula",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    schedule = models.ForeignKey(
        "academic.Schedule",
        verbose_name="horário",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    date = models.DateField("data")
    status = models.CharField("estado", max_length=20, choices=Status.choices)
    justification_text = models.TextField("justificação", blank=True, default="")
    justification_attachment = models.FileField(
        "anexo da justificação",
        upload_to=justification_attachment_upload_to,
        blank=True,
        null=True,
        help_text=(
            "RF-FREQ-02/docs/09-seguranca-e-privacidade.md §9.3: nunca servido por "
            "URL pública directa -- acesso mediado por "
            "apps.attendance.views.justification_attachment_view."
        ),
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registado por",
        on_delete=models.PROTECT,
        related_name="attendance_records_registered",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "presença"
        verbose_name_plural = "presenças"
        # Campos terminais apenas -- ver o mesmo cuidado documentado em
        # `grading.Grade.Meta`/`grading.FinalGrade.Meta` contra a explosão
        # de joins ao ordenar por um FK em bruto.
        ordering = ["-date", "student__first_name", "student__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "schedule", "date"],
                name="unique_attendance_per_enrollment_schedule_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.schedule} ({self.date}): {self.get_status_display()}"

    def clean(self):
        errors = {}

        for field_name, label in (
            ("student", "aluno"),
            ("enrollment", "matrícula"),
            ("schedule", "horário"),
            ("registered_by", "utilizador que registou"),
        ):
            related = getattr(self, field_name, None)
            institution_id = getattr(related, "institution_id", None)
            if (
                related is not None
                and self.institution_id
                and institution_id not in (None, self.institution_id)
            ):
                errors[field_name] = f"O(a) {label} tem de pertencer à mesma instituição."

        if self.enrollment_id and self.student_id and self.enrollment.student_id != self.student_id:
            errors["enrollment"] = "A matrícula tem de pertencer ao mesmo aluno."

        if self.date and self.schedule_id:
            from apps.academic.models import Schedule

            weekday_by_python_index = {
                0: Schedule.Weekday.MONDAY,
                1: Schedule.Weekday.TUESDAY,
                2: Schedule.Weekday.WEDNESDAY,
                3: Schedule.Weekday.THURSDAY,
                4: Schedule.Weekday.FRIDAY,
                5: Schedule.Weekday.SATURDAY,
            }
            expected_weekday = weekday_by_python_index.get(self.date.weekday())
            if expected_weekday is None:
                errors["date"] = "Não há aulas ao domingo."
            elif self.schedule.weekday != expected_weekday:
                errors["date"] = (
                    f"A data tem de corresponder a uma {self.schedule.get_weekday_display()} "
                    "(dia do horário)."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
