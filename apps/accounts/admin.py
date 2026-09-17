"""Django Admin registration for the `accounts` app's models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "FenixSchool",
            {
                "fields": (
                    "institution",
                    "created_by",
                    "profile",
                    "phone",
                    "preferred_language",
                    "is_2fa_active",
                )
            },
        ),
    )
    list_display = ("username", "email", "profile", "institution", "is_staff")
    list_filter = (*UserAdmin.list_filter, "profile", "institution")
    autocomplete_fields = ("institution",)

    def get_readonly_fields(self, request, obj=None):
        # `institution` is set once at account creation and never edited
        # through an ordinary form afterwards (issue #21's acceptance
        # criterion, docs/04-arquitetura-tecnica.md §4.4.1) -- editable only
        # on the add form, read-only on every subsequent change form.
        readonly = super().get_readonly_fields(request, obj)
        if obj is not None:
            return (*readonly, "institution")
        return readonly
