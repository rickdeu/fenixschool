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
    # `document_number` removido de `search_fields` (issue #141): fica
    # cifrado em repouso com uma cifra determinística, que só suporta
    # comparação de igualdade -- a busca `icontains` que o Django Admin usa
    # por omissão não tem como funcionar sobre o texto cifrado. Sem perda
    # real: o Django Admin nunca é o ecrã real usado por utilizadores finais
    # neste projecto.
    search_fields = ("full_name",)
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
    # Terminal (non-relation) fields only, not a bare "student" -- see
    # `grading.Grade.Meta`'s own comment on why ordering by a bare FK risks
    # a runaway join explosion via that related model's own `Meta.ordering`.
    ordering = ("student__first_name", "student__last_name")
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
    actions = ["calcular_situacao_final_action"]
    # Terminal (non-relation) fields only, not a bare "student" -- same
    # reasoning as `StudentGuardianAdmin.ordering`. Overrides `Enrollment`'s
    # own `Meta.ordering` (most recent matrícula first) only for this
    # listing -- the model's default still serves other consumers (e.g. a
    # student's own enrolment history) correctly as-is.
    ordering = ("student__first_name", "student__last_name")
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

    @admin.action(description="Calcular situação final")
    def calcular_situacao_final_action(self, request, queryset):
        # Local import: `enrollment` is a foundational app `grading` already
        # depends on -- reaching the other way, only inside this one action,
        # avoids `enrollment` importing `grading` at module load time (same
        # reasoning as `core.services.setup_institution`'s own local import
        # of `grading.services`).
        from apps.grading.services import calcular_situacao_final

        for enrollment in queryset:
            calcular_situacao_final(enrollment)
        self.message_user(
            request, f"Situação final calculada para {queryset.count()} matrícula(s)."
        )
