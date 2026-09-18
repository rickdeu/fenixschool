"""Modelo Horário (RF-CURR-06, docs/05-modelo-de-dados.md §5.10, issue #36)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SyncedModel

from .room_model import Room
from .school_class_model import SchoolClass
from .subject_model import Subject


class Schedule(SyncedModel):
    """ "Horário" -- a weekly recurring class slot: which Turma has which
    Disciplina, on which day/time, in which Sala, taught by which docente.

    `teacher` is a plain `accounts.User` (profile Docente/Diretor de Turma),
    not the `hr.Funcionario` §5.10 itself specifies: `hr.Funcionario` doesn't
    exist yet (M3 -- see `SchoolClass.director_turma`'s own docstring for the
    same reasoning). Unlike that field, this one can't just be left out
    until M3: a schedule that doesn't say who teaches isn't useful for
    anything (RF-RH-02's "associação de docentes a turmas", or attendance,
    both explicitly listed among this issue's acceptance criteria) -- every
    teacher already has a real `accounts.User` row that identifies them
    uniquely today, so this points there instead of fabricating a
    `hr.Funcionario` ahead of schedule.
    """

    class Weekday(models.TextChoices):
        MONDAY = "monday", "Segunda-feira"
        TUESDAY = "tuesday", "Terça-feira"
        WEDNESDAY = "wednesday", "Quarta-feira"
        THURSDAY = "thursday", "Quinta-feira"
        FRIDAY = "friday", "Sexta-feira"
        SATURDAY = "saturday", "Sábado"

    class Regime(models.TextChoices):
        THEORETICAL = "theoretical", "Teórica"
        PRACTICAL = "practical", "Prática"
        THEORETICAL_PRACTICAL = "theoretical_practical", "Teórico-Prática"

    school_class = models.ForeignKey(
        SchoolClass,
        verbose_name="turma",
        on_delete=models.PROTECT,
        related_name="schedule_slots",
    )
    subject = models.ForeignKey(
        Subject,
        verbose_name="disciplina",
        on_delete=models.PROTECT,
        related_name="schedule_slots",
    )
    weekday = models.CharField("dia da semana", max_length=10, choices=Weekday.choices)
    start_time = models.TimeField("hora de início")
    end_time = models.TimeField("hora de fim")
    regime = models.CharField("regime", max_length=25, choices=Regime.choices)
    room = models.ForeignKey(
        Room, verbose_name="sala", on_delete=models.PROTECT, related_name="schedule_slots"
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="docente",
        on_delete=models.PROTECT,
        related_name="schedule_slots",
    )

    class Meta(SyncedModel.Meta):
        verbose_name = "horário"
        verbose_name_plural = "horários"
        ordering = ["weekday", "start_time"]

    def __str__(self) -> str:
        return (
            f"{self.school_class} - {self.subject} "
            f"({self.get_weekday_display()} {self.start_time}-{self.end_time})"
        )

    def clean(self):
        errors = {}

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = "A hora de fim deve ser posterior à hora de início."

        for field_name, label in (
            ("school_class", "turma"),
            ("subject", "disciplina"),
            ("room", "sala"),
        ):
            related = getattr(self, field_name, None)
            if (
                related is not None
                and self.institution_id
                and related.institution_id != self.institution_id
            ):
                errors[field_name] = f"A {label} tem de pertencer à mesma instituição."

        if (
            self.teacher_id
            and self.institution_id
            and self.teacher.institution_id != self.institution_id
        ):
            errors["teacher"] = "O docente tem de pertencer à mesma instituição."

        if self.teacher_id:
            from apps.accounts.models import Profile

            if self.teacher.profile not in (Profile.TEACHER, Profile.HOMEROOM_TEACHER):
                errors["teacher"] = "O utilizador escolhido não tem o perfil de Docente."

        if (
            self.subject_id
            and self.school_class_id
            and self.subject.curricular_year_id != self.school_class.curricular_year_id
        ):
            errors["subject"] = "A disciplina tem de pertencer ao mesmo ano curricular da turma."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
