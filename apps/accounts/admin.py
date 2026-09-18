"""Django Admin registration for the `accounts` app's models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ADD_FORM_EXCLUDED_FIELDS = ("is_2fa_active", "failed_login_attempts", "locked_until")

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
        (
            "Bloqueio de conta (issue #26)",
            {"fields": ("failed_login_attempts", "locked_until")},
        ),
    )
    list_display = (
        "username",
        "email",
        "profile",
        "institution",
        "is_staff",
        "is_locked_display",
    )
    list_filter = (*UserAdmin.list_filter, "profile", "institution")
    autocomplete_fields = ("institution",)
    actions = ["unlock_accounts"]

    @admin.display(description="Bloqueada", boolean=True)
    def is_locked_display(self, user: User) -> bool:
        return user.is_locked

    @admin.action(description="Desbloquear conta(s) seleccionada(s)")
    def unlock_accounts(self, request, queryset):
        for user in queryset:
            user.unlock()
        self.message_user(request, f"{queryset.count()} conta(s) desbloqueada(s).")

    def get_fieldsets(self, request, obj=None):
        # These only reflect real state once the user exists (issue #25's
        # `TOTPDevice`, issue #26's lockout counters) -- keep them out of
        # the add form entirely, rather than showing meaningless zero/False
        # values for a user that doesn't exist yet.
        fieldsets = super().get_fieldsets(request, obj)
        if obj is not None:
            return fieldsets
        return tuple(
            (
                title,
                {
                    **options,
                    "fields": tuple(
                        f for f in options["fields"] if f not in self.ADD_FORM_EXCLUDED_FIELDS
                    ),
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
        # #25), never directly settable. `failed_login_attempts`/
        # `locked_until` (issue #26) are also read-only here -- unlocking
        # is done via the "Desbloquear conta(s)" action below, not by
        # hand-editing these counters. `groups` (issue #113) is always
        # derived from `profile` (see `accounts.signals.
        # sync_group_on_profile_change`) -- editing it directly here would
        # look like it worked, then silently revert on the next save.
        readonly = (
            *super().get_readonly_fields(request, obj),
            "is_2fa_active",
            "failed_login_attempts",
            "locked_until",
            "groups",
        )
        if obj is not None:
            return (*readonly, "institution")
        return readonly
