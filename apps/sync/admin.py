"""Registo dos modelos de `sync` no Django Admin."""

from django.contrib import admin

from .models import ChangeRecord, Node, SyncSession


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("id", "node_type", "institution", "last_synced_at", "created_at")
    list_filter = ("node_type",)
    search_fields = ("institution__name",)
    autocomplete_fields = ("institution",)
    readonly_fields = ("id", "created_at", "public_key")


@admin.register(ChangeRecord)
class ChangeRecordAdmin(admin.ModelAdmin):
    # Immutable audit trail of what happened, not a screen to edit -- see
    # docs/09-seguranca-e-privacidade.md §9.4 (auditoria).
    list_display = ("entity", "entity_id", "operation", "origin_node_id", "created_at", "synced_at")
    list_filter = ("operation",)
    search_fields = ("entity",)
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "entity",
        "entity_id",
        "operation",
        "payload",
        "origin_node_id",
        "created_at",
        "synced_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SyncSession)
class SyncSessionAdmin(admin.ModelAdmin):
    list_display = (
        "node",
        "status",
        "started_at",
        "finished_at",
        "records_sent",
        "records_received",
    )
    list_filter = ("status", "node")
    autocomplete_fields = ("node",)
    readonly_fields = ("id", "started_at")
