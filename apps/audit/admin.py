"""Registo dos modelos de `audit` no Django Admin.

Painel de auditoria (RF-ADM-03) por agora: pesquisa por entidade/utilizador
via o próprio Django Admin, até uma UI dedicada ser construída
(docs/06-modulos-e-funcionalidades.md). Sempre só de leitura -- os registos
são imutáveis (ver `AuditLogEntry.save()`/`delete()`).
"""

from django.contrib import admin

from .models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "entity", "entity_id", "user", "ip_address")
    list_filter = ("action", "entity")
    search_fields = ("entity", "entity_id", "user__username", "user__email")
    autocomplete_fields = ("user",)
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
