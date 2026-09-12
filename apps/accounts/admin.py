"""Django Admin registration for the `accounts` app's models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        *UserAdmin.fieldsets,
        ("FenixSchool", {"fields": ("institution", "created_by", "profile")}),
    )
    list_display = ("username", "email", "profile", "institution", "is_staff")
    list_filter = (*UserAdmin.list_filter, "profile", "institution")
