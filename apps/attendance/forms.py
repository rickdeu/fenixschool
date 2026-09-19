"""Formulários Django da app `attendance`."""

from datetime import date as date_cls

from django import forms
from django.core.exceptions import ValidationError

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
