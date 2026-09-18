"""Mapa de ocupação de salas e docentes (issue #38, RF-CURR-06,
docs/06-modulos-e-funcionalidades.md §6.5) -- reutiliza os dados de
`academic.Schedule` (issue #36), filtrável por sala, docente ou turma."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render

from apps.academic.models import Room, Schedule, SchoolClass
from apps.accounts.models import Profile, User
from apps.core.view_helpers import require_institution_context


@login_required
@permission_required("academic.view_schedule", raise_exception=True)
def schedule_occupancy_view(request):
    redirect_response = require_institution_context(request)
    if redirect_response:
        return redirect_response

    institution = request.institution

    schedules = Schedule.objects.filter(institution=institution).select_related(
        "school_class", "subject", "room", "teacher"
    )

    room_id = request.GET.get("room") or ""
    teacher_id = request.GET.get("teacher") or ""
    school_class_id = request.GET.get("school_class") or ""
    if room_id:
        schedules = schedules.filter(room_id=room_id)
    if teacher_id:
        schedules = schedules.filter(teacher_id=teacher_id)
    if school_class_id:
        schedules = schedules.filter(school_class_id=school_class_id)

    slots_by_weekday = {weekday: [] for weekday, _ in Schedule.Weekday.choices}
    for slot in schedules.order_by("start_time"):
        slots_by_weekday[slot.weekday].append(slot)
    # A list of (label, slots) tuples, not a dict keyed by weekday -- Django
    # templates can't look up a dict by a variable key without a custom
    # filter, only by a literal one.
    grid = [(label, slots_by_weekday[weekday]) for weekday, label in Schedule.Weekday.choices]

    return render(
        request,
        "admin_panel/schedule_occupancy.html",
        {
            "grid": grid,
            "rooms": Room.objects.filter(institution=institution).order_by("designation"),
            "teachers": User.objects.filter(
                institution=institution, profile__in=[Profile.TEACHER, Profile.HOMEROOM_TEACHER]
            ).order_by("last_name", "first_name"),
            "school_classes": SchoolClass.objects.filter(institution=institution).order_by(
                "designation"
            ),
            "selected_room": room_id,
            "selected_teacher": teacher_id,
            "selected_school_class": school_class_id,
        },
    )
