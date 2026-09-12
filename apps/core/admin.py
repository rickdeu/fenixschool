"""Django Admin registrations for the `core` app's models."""

from django.contrib import admin

from .models import (
    IdentificationDocumentType,
    Institution,
    MobileOperator,
    Municipality,
    Profession,
    Province,
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "code")
    list_filter = ("province",)
    search_fields = ("name", "code")


@admin.register(MobileOperator)
class MobileOperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(IdentificationDocumentType)
class IdentificationDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
