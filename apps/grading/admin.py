"""Registo dos modelos de `grading` no Django Admin."""

from django.contrib import admin

from .forms import FinalGradeAdminForm, GradeAdminForm
from .models import EvaluationType, FinalGrade, Grade, GradingFormulaOverride, GradingScale
from .services import ajustar_media_manualmente


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
        "qualitative_level",
        "school_class",
        "is_grade_report_closed",
        "institution",
    )
    # Explicit and shallow (one hop each) on purpose: `list_display` above is
    # almost all FK columns, and Django's Admin auto-adds a *bare*
    # `select_related()` (no args -- recursive, follows every non-null FK at
    # every level) whenever `list_select_related` is left at its default
    # `False` and any `list_display` field is a relation. Combined with this
    # model's own dense FK graph (student/subject/school_class -> course/
    # curricular_year/department/cycle, each with their own `institution`
    # FK), that blew up into a single changelist query joining
    # `core_institution` 30+ times over -- hit SQLite's 64-table join limit
    # outright, and would still be a needlessly enormous query in Postgres.
    list_select_related = ("student", "subject", "evaluation_type", "school_class", "institution")
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
        "qualitative_level",
    )


@admin.register(FinalGrade)
class FinalGradeAdmin(admin.ModelAdmin):
    form = FinalGradeAdminForm
    list_display = (
        "enrollment",
        "subject",
        "academic_term",
        "calculated_value",
        "final_value",
        "qualitative_level",
        "institution",
    )
    # See `GradeAdmin.list_select_related`'s own comment: same fix, same
    # reasoning -- `list_display` above is mostly FK columns.
    list_select_related = ("enrollment", "subject", "academic_term", "institution")
    list_filter = ("institution", "academic_term")
    search_fields = (
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "subject__name",
    )
    autocomplete_fields = ("institution", "enrollment", "subject", "academic_term")
    readonly_fields = (
        "calculated_value",
        "final_value",
        "qualitative_level",
        "overridden_by",
        "overridden_at",
    )

    def has_add_permission(self, request):
        # Uma FinalGrade só existe a partir de um cálculo real
        # (`apps.grading.services.registar_media_final`) sobre Notas já
        # lançadas -- nunca inserida à mão, mesmo raciocínio dos campos
        # derivados de `Grade`.
        return False

    def save_model(self, request, obj, form, change):
        if "manual_override_value" in form.changed_data and obj.manual_override_value is not None:
            ajustar_media_manualmente(
                final_grade=obj,
                user=request.user,
                value=obj.manual_override_value,
                reason=obj.override_reason,
            )
        else:
            super().save_model(request, obj, form, change)
