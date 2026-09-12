"""Django Admin registrations for the `core` app's models."""

from django.contrib import admin

from .forms import (
    IdentificationDocumentTypeAdminForm,
    MobileOperatorAdminForm,
    MunicipalityAdminForm,
    ProfessionAdminForm,
    ProvinceAdminForm,
)
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


class MunicipalityInline(admin.TabularInline):
    """Lets a province's municipalities be reviewed/added from its own admin
    page, instead of hunting for them in the separate `Municipality` list."""

    model = Municipality
    form = MunicipalityAdminForm
    fields = ("name", "code")
    extra = 1


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    form = ProvinceAdminForm
    list_display = ("name", "code", "municipality_count")
    search_fields = ("name", "code")
    inlines = [MunicipalityInline]

    @admin.display(description="Municípios")
    def municipality_count(self, province: Province) -> int:
        return province.municipalities.count()


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    form = MunicipalityAdminForm
    list_display = ("name", "province", "code")
    list_filter = ("province",)
    search_fields = ("name", "code")
    autocomplete_fields = ("province",)


@admin.register(MobileOperator)
class MobileOperatorAdmin(admin.ModelAdmin):
    form = MobileOperatorAdminForm
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(IdentificationDocumentType)
class IdentificationDocumentTypeAdmin(admin.ModelAdmin):
    form = IdentificationDocumentTypeAdminForm
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    form = ProfessionAdminForm
    list_display = ("name", "code")
    search_fields = ("name", "code")
