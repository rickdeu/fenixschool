"""Registo dos modelos de `academic` no Django Admin."""

from django.contrib import admin, messages

from .forms import ScheduleAdminForm
from .models import Course, CurricularYear, Department, Room, Schedule, SchoolClass, Subject


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "institution")
    list_filter = ("institution",)
    search_fields = ("name",)
    autocomplete_fields = ("institution",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department", "cycle", "duration_years", "institution")
    list_filter = ("institution", "department", "cycle")
    search_fields = ("name", "code", "ministry_of_education_code")
    autocomplete_fields = ("institution", "department", "cycle")


@admin.register(CurricularYear)
class CurricularYearAdmin(admin.ModelAdmin):
    list_display = ("course", "number", "equivalent_grade", "institution")
    list_filter = ("institution", "course")
    search_fields = ("equivalent_grade", "course__name")
    autocomplete_fields = ("institution", "course")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "course",
        "curricular_year",
        "subject_type",
        "weekly_hours",
        "institution",
    )
    list_filter = ("institution", "course", "subject_type")
    search_fields = ("name", "code")
    autocomplete_fields = ("institution", "course", "curricular_year", "term", "cycle")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("designation", "capacity", "institution")
    list_filter = ("institution",)
    search_fields = ("designation",)
    autocomplete_fields = ("institution",)


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = (
        "designation",
        "code",
        "academic_year",
        "course",
        "curricular_year",
        "shift",
        "max_enrollment",
        "institution",
    )
    list_filter = ("institution", "academic_year", "shift", "course")
    search_fields = ("designation", "code")
    autocomplete_fields = (
        "institution",
        "academic_year",
        "academic_term",
        "course",
        "curricular_year",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Issue #174 (RF-CURR-05): "aviso, não bloqueio automático" -- o
        # tecto legal (Decreto Presidencial 162/23) nunca impede a
        # gravação, só avisa quem a fez.
        if obj.exceeds_legal_enrollment_ceiling:
            self.message_user(
                request,
                f"O número máximo de inscritos ({obj.max_enrollment}) ultrapassa o tecto "
                f"legal do Decreto Presidencial 162/23 ({obj.LEGAL_MAX_ENROLLMENT_CEILING}).",
                level=messages.WARNING,
            )


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    form = ScheduleAdminForm
    list_display = (
        "school_class",
        "subject",
        "weekday",
        "start_time",
        "end_time",
        "room",
        "teacher",
        "institution",
    )
    list_filter = ("institution", "weekday", "regime")
    search_fields = ("school_class__designation", "subject__name")
    autocomplete_fields = ("institution", "school_class", "subject", "room", "teacher")
