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
    AcademicCycle,
    AcademicTerm,
    AcademicYear,
    IdentificationDocumentType,
    Institution,
    MobileOperator,
    Municipality,
    NonTeachingDay,
    Profession,
    Province,
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tax_id",
        "ministry_of_education_code",
        "municipality",
        "created_at",
    )
    search_fields = ("name", "tax_id", "ministry_of_education_code")
    autocomplete_fields = ("province", "municipality")
    fieldsets = (
        (
            "Identificação",
            {"fields": ("name", "tax_id", "ministry_of_education_code", "description")},
        ),
        (
            "Morada",
            {
                "fields": (
                    "province",
                    "municipality",
                    "district_or_commune",
                    "neighborhood",
                    "street",
                    "house_number",
                )
            },
        ),
        (
            "Contactos",
            {
                "fields": (
                    "landline_phone",
                    "unitel_phone",
                    "movicel_phone",
                    "africell_phone",
                    "email",
                    "website",
                )
            },
        ),
        ("Identidade visual", {"fields": ("logo",)}),
        (
            "Parametrização",
            {"fields": ("default_grading_formula", "blocks_documents_with_outstanding_debt")},
        ),
    )


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


class AcademicTermInline(admin.TabularInline):
    model = AcademicTerm
    fields = ("number", "start_date", "end_date")
    extra = 1


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("designation", "institution", "start_date", "end_date", "is_current")
    list_filter = ("is_current", "institution")
    search_fields = ("designation",)
    autocomplete_fields = ("institution",)
    inlines = [AcademicTermInline]


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ("academic_year", "number", "start_date", "end_date")
    list_filter = ("academic_year__institution",)
    search_fields = ("academic_year__designation",)
    autocomplete_fields = ("academic_year", "institution")


@admin.register(AcademicCycle)
class AcademicCycleAdmin(admin.ModelAdmin):
    list_display = ("designation", "order", "institution")
    list_filter = ("institution",)
    search_fields = ("designation",)
    autocomplete_fields = ("institution",)


@admin.register(NonTeachingDay)
class NonTeachingDayAdmin(admin.ModelAdmin):
    list_display = ("description", "date", "scope", "institution")
    list_filter = ("scope", "institution")
    search_fields = ("description",)
    autocomplete_fields = ("institution",)
