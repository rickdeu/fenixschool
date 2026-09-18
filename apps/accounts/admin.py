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

    def get_fieldsets(self, request, obj=None):
        # `is_2fa_active` only reflects real state once the user exists
        # (issue #25's `TOTPDevice`) -- keep it out of the add form
        # entirely, rather than showing an always-False property for a
        # user that doesn't exist yet.
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None:
            return fieldsets
        return tuple(
            (
                title,
                {
                    **options,
                    "fields": tuple(f for f in options["fields"] if f != "is_2fa_active"),
                },
            )
            for title, options in fieldsets
        )

    def get_readonly_fields(self, request, obj=None):
        # `institution` is set once at account creation and never edited
        # through an ordinary form afterwards (issue #21's acceptance
        # criterion, docs/04-arquitetura-tecnica.md §4.4.1) -- editable only
        # on the add form, read-only on every subsequent change form.
        # `is_2fa_active` is always read-only: a computed property (issue
        # #25), never directly settable.
        readonly = (*super().get_readonly_fields(request, obj), "is_2fa_active")
        if obj is not None:
            return (*readonly, "institution")
        return readonly
