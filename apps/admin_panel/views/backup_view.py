"""Ecrã de cópias de segurança da base de dados (issue #166, RF-INST-*,
docs/11-implantacao-e-operacoes.md §11.4)."""

import os
from datetime import datetime
from pathlib import Path

from django.apps import apps as django_apps
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.messages import success
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from apps.core.services import backup_database


def _backup_dir() -> Path:
    return Path(os.environ.get("BACKUP_DIR", "/app/backups"))


def _list_backups() -> list[dict]:
    backup_dir = _backup_dir()
    if not backup_dir.exists():
        return []
    files = sorted(
        backup_dir.glob("fenixschool-*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    return [
        {
            "name": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime),
        }
        for f in files
    ]


def _next_scheduled_run():
    # The daily schedule (apps.core.signals.schedule_automatic_backup) only
    # exists under the local node's settings module -- see that signal's own
    # docstring for why django_q isn't installed everywhere.
    if not django_apps.is_installed("django_q"):
        return None
    from django_q.models import Schedule

    schedule = Schedule.objects.filter(func="apps.core.services.backup_database").first()
    return schedule.next_run if schedule else None


@login_required
@permission_required("core.change_institution", raise_exception=True)
def backup_list_view(request):
    if request.method == "POST" and "run_now" in request.POST:
        backup_database()
        success(request, "Cópia de segurança criada com sucesso.")
        return redirect("admin_panel:backup_list")

    return render(
        request,
        "admin_panel/backup_list.html",
        {
            "backups": _list_backups(),
            "next_scheduled_run": _next_scheduled_run(),
            "automatic_backup_configured": django_apps.is_installed("django_q"),
        },
    )


@login_required
@permission_required("core.change_institution", raise_exception=True)
def backup_download_view(request, filename):
    backup_dir = _backup_dir().resolve()
    resolved = (backup_dir / filename).resolve()

    # Path-traversal guard: `filename` comes straight from the URL, and a
    # single `<str:...>` segment can't contain "/" (Django's own converter
    # already excludes it), but ".." alone still resolves outside `backup_dir`.
    if (
        not resolved.is_relative_to(backup_dir)
        or not resolved.name.startswith("fenixschool-")
        or not resolved.exists()
    ):
        raise Http404

    return FileResponse(open(resolved, "rb"), as_attachment=True, filename=resolved.name)
