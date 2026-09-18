"""Registo dos modelos de `grading` no Django Admin."""

from django.contrib import admin

from .models import EvaluationType, GradingFormulaOverride


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
