"""Registo dos modelos de `enrollment` no Django Admin."""

from django.contrib import admin

from .models import Guardian, Student, StudentGuardian


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    fk_name = "student"
    fields = ("guardian", "is_primary", "financially_responsible")
    autocomplete_fields = ("guardian",)
    extra = 1


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_number",
        "first_name",
        "last_name",
        "document_number",
        "status",
        "institution",
    )
    list_filter = ("institution", "status", "gender")
    search_fields = ("first_name", "last_name", "document_number", "student_number")
    autocomplete_fields = (
        "institution",
        "document_type",
        "province",
        "municipality",
        "profession",
    )
    readonly_fields = ("student_number", "registration_date")
    inlines = [StudentGuardianInline]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("full_name", "kinship", "document_number", "institution")
    list_filter = ("institution", "kinship")
    search_fields = ("full_name", "document_number")
    autocomplete_fields = (
        "institution",
        "document_type",
        "province",
        "municipality",
        "user",
    )


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ("student", "guardian", "is_primary", "financially_responsible")
    list_filter = ("institution", "is_primary")
    autocomplete_fields = ("institution", "student", "guardian")
