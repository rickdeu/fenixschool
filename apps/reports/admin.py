"""Registo dos modelos de `reports` no Django Admin.

Apenas inspecção crua (nunca a via real para um utilizador -- ver
docs/12-plano-de-implementacao.md e o histórico de decisões deste
projecto): `IssuedDocument` é um registo histórico imutável, nunca criado
nem editado à mão, sempre via `apps.reports.services.emitir_documento`.
"""

from django.contrib import admin

from .models import IssuedDocument


@admin.register(IssuedDocument)
class IssuedDocumentAdmin(admin.ModelAdmin):
    list_display = ("formatted_number", "document_type", "issued_by", "institution", "created_at")
    list_select_related = ("issued_by", "institution")
    list_filter = ("institution", "document_type")
    search_fields = ("formatted_number",)
    autocomplete_fields = ("institution", "issued_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
