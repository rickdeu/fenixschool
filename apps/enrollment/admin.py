"""Registo dos modelos de `enrollment` no Django Admin."""

from django.contrib import admin

from .models import Candidate, Enrollment, Guardian, Student, StudentGuardian


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
        "guardian_consent_given_by",
    )
    readonly_fields = ("student_number", "registration_date", "guardian_consent_given_at")
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


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("full_name", "desired_course", "status", "application_date", "institution")
    list_filter = ("institution", "status", "desired_course")
    search_fields = ("full_name", "contact")
    autocomplete_fields = ("institution", "desired_course")
    readonly_fields = ("application_date",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment_number",
        "student",
        "academic_year",
        "school_class",
        "status",
        "is_repeating",
        "institution",
    )
    list_filter = ("institution", "academic_year", "status", "is_repeating")
    search_fields = ("student__first_name", "student__last_name", "enrollment_number")
    autocomplete_fields = (
        "institution",
        "student",
        "course",
        "academic_year",
        "school_class",
        "cycle",
        "curricular_year",
        "presented_document_type",
        "previous_enrollment",
    )
    readonly_fields = ("enrollment_number", "date")
