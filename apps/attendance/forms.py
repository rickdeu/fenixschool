"""Formulários Django da app `attendance`."""

from datetime import date as date_cls

from django import forms
from django.core.exceptions import ValidationError

from apps.academic.models import Schedule

from .services import get_docente_schedule_slots


class AttendanceGridSelectionForm(forms.Form):
    """Issue #66's primeiro passo: escolher para que horário/dia marcar
    presenças. `schedule` só oferece os horários que `teacher` de facto lecciona
    (`get_docente_schedule_slots`, via `academic.Schedule`)."""

    schedule = forms.ChoiceField(label="Horário")
    date = forms.DateField(
        label="Data", initial=date_cls.today, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        slots = list(get_docente_schedule_slots(teacher))
        self.schedules_by_id = {str(slot.id): slot for slot in slots}
        self.fields["schedule"].choices = [
            (
                str(slot.id),
                f"{slot.school_class} — {slot.subject} "
                f"({slot.get_weekday_display()} {slot.start_time}-{slot.end_time})",
            )
            for slot in slots
        ]

    def clean_schedule(self):
        key = self.cleaned_data["schedule"]
        if key not in self.schedules_by_id:
            raise ValidationError("Horário inválido.")
        return key

    def clean(self):
        cleaned_data = super().clean()
        schedule_key = cleaned_data.get("schedule")
        attendance_date = cleaned_data.get("date")
        if schedule_key is None or attendance_date is None:
            return cleaned_data

        # A data por omissão é sempre "hoje" (ver `initial=date_cls.today`
        # acima), independentemente do dia da semana do horário escolhido --
        # sem esta validação, submeter o formulário sem alterar a data
        # redirecciona para a grelha e só falha, de forma confusa, ao
        # tentar gravar (`Attendance.clean()`).
        weekday_by_python_index = dict(enumerate(Schedule.Weekday.values))
        expected_weekday = weekday_by_python_index.get(attendance_date.weekday())
        schedule = self.schedules_by_id[schedule_key]
        if expected_weekday is None:
            self.add_error("date", "Não há aulas ao domingo.")
        elif schedule.weekday != expected_weekday:
            self.add_error(
                "date",
                f"A data tem de corresponder a uma {schedule.get_weekday_display()} "
                "(dia do horário escolhido).",
            )
        return cleaned_data
