"""Formulários Django da app `guardian_portal`."""

from django import forms
from django.utils.translation import gettext_lazy as _


class StudentSelectorForm(forms.Form):
    """RF-MAT-12's "selector de educando" (issue #52) -- choices are built
    dynamically per request from the guardian's own students, never a
    hardcoded/global list.
    """

    student = forms.ChoiceField(label=_("Educando"))

    def __init__(self, *args, students, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].choices = [
            (str(student.id), f"{student.first_name} {student.last_name}") for student in students
        ]
