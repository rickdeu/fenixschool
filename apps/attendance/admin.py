"""Registo dos modelos de `attendance` no Django Admin.

Apenas inspecção crua (nunca a via real para um utilizador -- o registo
diário faz-se sempre pelo ecrã próprio de `attendance`, issue #66)."""

from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "schedule", "date", "status", "institution")
    list_select_related = ("student", "schedule", "institution")
    list_filter = ("institution", "status", "date")
    search_fields = ("student__first_name", "student__last_name")
    autocomplete_fields = ("institution", "student", "enrollment", "schedule", "registered_by")
