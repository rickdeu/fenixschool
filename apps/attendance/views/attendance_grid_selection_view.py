"""Selecção de horário/dia antes da grelha de marcação de presença (issue
#66)."""

from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import AttendanceGridSelectionForm
from ..permissions import docente_required


@docente_required
def attendance_grid_selection_view(request):
    form = AttendanceGridSelectionForm(request.POST or None, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        query = urlencode(
            {
                "horario": form.cleaned_data["schedule"],
                "data": form.cleaned_data["date"].isoformat(),
            }
        )
        return redirect(f"{reverse('attendance:attendance_grid')}?{query}")

    return render(request, "attendance/attendance_grid_selection.html", {"form": form})
