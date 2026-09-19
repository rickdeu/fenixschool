"""Formulários Django da app `academic`."""

from django import forms
from django.core.exceptions import ValidationError

from apps.core.models import AcademicTerm, AcademicYear

from .models import Course, CurricularYear, Schedule, SchoolClass
from .services import ScheduleConflictError, validate_schedule_conflict


class SchoolClassForm(forms.ModelForm):
    """Turma (RF-CURR-05, issue #34) -- até agora só editável via Django
    Admin; ecrã dedicado pedido directamente pelo utilizador."""

    class Meta:
        model = SchoolClass
        fields = [
            "code",
            "designation",
            "academic_year",
            "course",
            "curricular_year",
            "academic_term",
            "shift",
            "max_enrollment",
        ]

    def __init__(self, *args, institution=None, **kwargs):
        super().__init__(*args, **kwargs)
        if institution is not None:
            self.fields["academic_year"].queryset = AcademicYear.objects.filter(
                institution=institution
            )
            self.fields["course"].queryset = Course.objects.filter(institution=institution)
            self.fields["curricular_year"].queryset = CurricularYear.objects.filter(
                institution=institution
            )
            self.fields["academic_term"].queryset = AcademicTerm.objects.filter(
                institution=institution
            )
        self.fields["academic_term"].required = False


class ScheduleAdminForm(forms.ModelForm):
    """Enforces `validate_schedule_conflict` (issue #37) on the only place
    `Schedule` rows can be created/edited today -- the Django Admin (issue
    #36 is model+admin only; a dedicated grid, issue #59, is separate,
    later M2 work)."""

    class Meta:
        model = Schedule
        fields = [
            "institution",
            "origin_node_id",
            "updated_by",
            "version",
            "is_deleted",
            "school_class",
            "subject",
            "weekday",
            "start_time",
            "end_time",
            "regime",
            "room",
            "teacher",
        ]

    def clean(self):
        cleaned_data = super().clean()
        # Only meaningful once every field this check needs is itself
        # already valid -- a missing/invalid `teacher`/`room`/`school_class`
        # would otherwise resolve to `None`, matching every other Schedule
        # that also has that field blank (impossible, since they're all
        # required, but never during this same validation pass).
        if self.errors:
            return cleaned_data

        candidate = Schedule(
            pk=self.instance.pk,
            institution=cleaned_data.get("institution"),
            **{
                field: cleaned_data[field]
                for field in (
                    "school_class",
                    "subject",
                    "weekday",
                    "start_time",
                    "end_time",
                    "room",
                    "teacher",
                )
            },
        )
        try:
            validate_schedule_conflict(candidate)
        except ScheduleConflictError as error:
            raise ValidationError(str(error)) from error
        return cleaned_data
