"""Registo dos modelos de `grading` no Django Admin."""

from django.contrib import admin

from .forms import GradeAdminForm
from .models import EvaluationType, Grade, GradingFormulaOverride, GradingScale


@admin.register(EvaluationType)
class EvaluationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "default_weight", "institution")
    list_filter = ("institution",)
    search_fields = ("name",)
    autocomplete_fields = ("institution",)


@admin.register(GradingFormulaOverride)
class GradingFormulaOverrideAdmin(admin.ModelAdmin):
    list_display = ("__str__", "course", "subject", "institution")
    list_filter = ("institution",)
    autocomplete_fields = ("institution", "course", "subject")


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
    list_display = ("level", "qualitative_level", "min_value", "max_value")
    ordering = ("level",)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    form = GradeAdminForm
    list_display = (
        "student",
        "subject",
        "evaluation_type",
        "value",
        "school_class",
        "is_grade_report_closed",
        "institution",
    )
    list_filter = ("institution", "is_grade_report_closed", "academic_year", "school_class")
    search_fields = ("student__first_name", "student__last_name", "subject__name")
    autocomplete_fields = (
        "institution",
        "student",
        "enrollment",
        "subject",
        "academic_term",
        "evaluation_type",
        "teacher",
    )
    readonly_fields = (
        "course",
        "academic_year",
        "cycle",
        "curricular_year",
        "school_class",
        "department",
    )
