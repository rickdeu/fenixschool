"""Registo dos modelos de `grading` no Django Admin."""

from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.template.response import TemplateResponse

from .forms import FinalGradeAdminForm, GradeAdminForm
from .models import (
    EvaluationType,
    FinalGrade,
    FinalSituation,
    Grade,
    GradingFormulaOverride,
    GradingScale,
)
from .services import (
    ReaberturaSemJustificacaoError,
    ajustar_media_manualmente,
    homologar_pauta,
    reabrir_pauta,
)


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
    actions = ["homologar_pauta_action", "reabrir_pauta_action"]
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
        "reopening_reason",
    )

    @admin.action(description="Homologar pauta (fechar as notas seleccionadas)")
    def homologar_pauta_action(self, request, queryset):
        count = homologar_pauta(queryset, user=request.user)
        self.message_user(request, f"{count} nota(s) homologada(s) e fechada(s).")

    @admin.action(description="Reabrir pauta (com justificação obrigatória)")
    def reabrir_pauta_action(self, request, queryset):
        if "apply" in request.POST:
            reason = request.POST.get("reason", "")
            try:
                count = reabrir_pauta(queryset, user=request.user, reason=reason)
            except ReaberturaSemJustificacaoError as error:
                self.message_user(request, str(error), level=messages.ERROR)
                return None
            self.message_user(request, f"{count} nota(s) reaberta(s).")
            return None

        return TemplateResponse(
            request,
            "grading/admin_reabrir_pauta_confirm.html",
            {
                "grades": queryset,
                "opts": self.model._meta,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "action_name": "reabrir_pauta_action",
            },
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


@admin.register(FinalSituation)
class FinalSituationAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "status", "calculated_at", "institution")
    list_select_related = ("enrollment", "institution")
    list_filter = ("institution", "status")
    search_fields = ("enrollment__student__first_name", "enrollment__student__last_name")
    autocomplete_fields = ("institution", "enrollment", "failed_subjects")
    readonly_fields = ("status", "failed_subjects", "calculated_at")

    def has_add_permission(self, request):
        # Uma FinalSituation só existe a partir de um cálculo real
        # (`apps.grading.services.calcular_situacao_final`, accionado pela
        # acção "Calcular situação final" em EnrollmentAdmin) -- nunca
        # inserida à mão, mesmo raciocínio dos campos derivados de `Grade`/
        # `FinalGrade`.
        return False

    def has_change_permission(self, request, obj=None):
        # Todos os campos são readonly (calculados) -- nada aqui é editável
        # à mão, só recalculável via a mesma acção.
        return False
